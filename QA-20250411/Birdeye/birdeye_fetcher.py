import json
import os
from datetime import datetime, timezone
import argparse
import requests
from dotenv import load_dotenv
import time
import pandas as pd
import math

# --- Environment & Config Loading ---
def load_api_key():
    """Loads the Birdeye API key from the .env file."""
    script_dir = os.path.dirname(__file__)
    dotenv_path = os.path.join(script_dir, '.env')
    load_dotenv(dotenv_path=dotenv_path)
    api_key = os.getenv("BIRDEYE_API_KEY")
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print("Error: BIRDEYE_API_KEY not found or not set in .env file.")
        print(f"Please create or update {dotenv_path}")
        return None
    print("API Key loaded successfully.")
    return api_key

def load_config(config_path="default_config.json"):
    """Loads the configuration file."""
    try:
        script_dir = os.path.dirname(__file__)
        abs_config_path = os.path.join(script_dir, config_path)
        with open(abs_config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"Configuration loaded successfully from {abs_config_path}")
        return config
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {abs_config_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {abs_config_path}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading config: {e}")
        return None

# --- Time Conversion ---
def iso_to_unix(iso_string):
    """Converts an ISO 8601 string to a Unix timestamp (integer seconds)."""
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        unix_timestamp = int(dt.timestamp())
        return unix_timestamp
    except ValueError:
        print(f"Error: Invalid ISO 8601 format for time string: {iso_string}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during time conversion: {e}")
        return None

def string_to_unix(time_str):
    """Converts a time string in 'YYYY-MM-DD HH:MM:SS' format to Unix timestamp."""
    try:
        dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        unix_timestamp = int(dt.timestamp())
        return unix_timestamp
    except ValueError:
        print(f"Error: Invalid time format for string: {time_str}")
        try:
            # Try ISO format as fallback
            return iso_to_unix(time_str)
        except:
            return None
    except Exception as e:
        print(f"An unexpected error occurred during time conversion: {e}")
        return None

# --- Date Range Chunking ---
def chunk_time_range(start_unix, end_unix, max_interval_hours=24):
    """
    Split a large time range into smaller chunks to avoid getting too much data in a single request.
    Returns a list of (chunk_start, chunk_end) tuples in Unix timestamp format.
    """
    # Convert max_interval from hours to seconds
    max_interval_seconds = max_interval_hours * 60 * 60
    
    # Calculate total duration in seconds
    total_duration = end_unix - start_unix
    
    # If the duration is already less than max_interval, return the original range
    if total_duration <= max_interval_seconds:
        return [(start_unix, end_unix)]
    
    # Calculate number of chunks needed
    num_chunks = math.ceil(total_duration / max_interval_seconds)
    
    # Calculate chunk size in seconds
    chunk_size = total_duration / num_chunks
    
    # Generate chunks
    chunks = []
    current_start = start_unix
    
    for i in range(num_chunks):
        if i == num_chunks - 1:
            # Last chunk should end at the original end time
            chunks.append((current_start, end_unix))
        else:
            chunk_end = current_start + chunk_size
            chunks.append((current_start, int(chunk_end)))
            current_start = int(chunk_end) + 1  # Add 1 second to avoid overlap
    
    return chunks

# --- API Call ---
def fetch_ohlcv_data(config, request_config, start_unix, end_unix, api_key, token_address=None):
    """Fetches OHLCV data for a specific request configuration."""
    base_url = config.get("common_parameters", {}).get("base_url")
    api_key_header = config.get("common_parameters", {}).get("api_key_header")
    endpoint = request_config.get("endpoint")
    query_params = request_config.get("query_params", {}).copy() # Use copy to avoid modifying original

    if not all([base_url, api_key_header, endpoint, query_params]):
        print(f"Error: Incomplete configuration for request '{request_config.get('name', 'Unnamed')}'")
        return None

    # Update time parameters
    query_params["time_from"] = start_unix
    query_params["time_to"] = end_unix
    
    # Update token address if provided
    if token_address:
        query_params["address"] = token_address
        print(f"Using custom token address: {token_address}")

    headers = {api_key_header: api_key}
    url = f"{base_url}{endpoint}"

    request_name = request_config.get('name', endpoint)
    print(f"\nAttempting API call for: {request_name}")
    print(f"URL: {url}")
    print(f"Params: {query_params}")
    # print(f"Headers: {{'{api_key_header}': '********'}}") # Don't print the actual key

    try:
        response = requests.get(url, headers=headers, params=query_params)
        response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)

        print(f"API call successful for {request_name} (Status: {response.status_code})")
        return response.json() # Return the parsed JSON data

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred for {request_name}: {http_err} (Status: {response.status_code})")
        print(f"Response Body: {response.text}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred for {request_name}: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred for {request_name}: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred during the request for {request_name}: {req_err}")
    except json.JSONDecodeError:
        print(f"Error decoding JSON response for {request_name}. Response Text: {response.text}")
    except Exception as e:
         print(f"An unexpected error occurred during API call for {request_name}: {e}")

    return None # Return None if any error occurred

# --- CSV Saving ---
def save_to_csv(data, filename, output_dir):
    """Saves the fetched OHLCV data items to a CSV file."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Full path to the output file
        filepath = os.path.join(output_dir, filename)
        
        # Extract the data items
        if "data" in data and "items" in data["data"]:
            items = data["data"]["items"]
            if not items:
                print(f"Warning: No items found in the response for {filename}.")
                return

            # Convert the items to a DataFrame
            df = pd.DataFrame(items)
            
            # Save to CSV
            df.to_csv(filepath, index=False)
            print(f"Data saved to {filepath} ({len(items)} records)")
        elif "data" in data and isinstance(data["data"], list):
            # Some endpoints return a list directly under 'data'
            items = data["data"]
            if not items:
                print(f"Warning: No items found in the response for {filename}.")
                return
                
            # Convert the items to a DataFrame
            df = pd.DataFrame(items)
            
            # Save to CSV
            df.to_csv(filepath, index=False)
            print(f"Data saved to {filepath} ({len(items)} records)")
        else:
            print(f"Warning: Unexpected data structure for {filename}. Could not find 'items' in response.")
            # Try to save whatever structure we got
            try:
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"Raw data saved to {filepath}")
            except Exception as e:
                print(f"Could not save raw data: {e}")
    except KeyError as e:
        print(f"Error processing data for {filename}: Missing expected key {e}")
        print("Data structure might have changed. Raw data:", data)
    except Exception as e:
        print(f"An unexpected error occurred while saving {filename} to CSV: {e}")


# Function to fetch and combine data from multiple time chunks
def fetch_and_combine_data(config, request_conf, chunks, api_key, token_address, rate_limit_sleep=1):
    """
    Fetch data for each time chunk and combine the results.
    Respects rate limits by sleeping between requests.
    """
    all_items = []
    request_name = request_conf.get("name", request_conf.get("endpoint", "unnamed_request"))
    
    print(f"\nFetching data for {request_name} in {len(chunks)} chunks:")
    
    for i, (chunk_start, chunk_end) in enumerate(chunks):
        print(f"\nChunk {i+1}/{len(chunks)}: {datetime.fromtimestamp(chunk_start, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} to {datetime.fromtimestamp(chunk_end, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Wait to respect rate limits (60 rpm = 1 request per second)
        if i > 0:
            print(f"Sleeping for {rate_limit_sleep} seconds to respect API rate limits...")
            time.sleep(rate_limit_sleep)
        
        # Fetch data for this chunk
        data = fetch_ohlcv_data(config, request_conf, chunk_start, chunk_end, api_key, token_address)
        
        if data is not None:
            # Extract items
            if "data" in data:
                if "items" in data["data"]:
                    items = data["data"]["items"]
                    if items:
                        all_items.extend(items)
                        print(f"Retrieved {len(items)} items from chunk {i+1}")
                    else:
                        print(f"No items found in chunk {i+1}")
                elif isinstance(data["data"], list):
                    items = data["data"]
                    if items:
                        all_items.extend(items)
                        print(f"Retrieved {len(items)} items from chunk {i+1}")
                    else:
                        print(f"No items found in chunk {i+1}")
                else:
                    print(f"Unexpected data structure in chunk {i+1}")
            else:
                print(f"No 'data' field found in response for chunk {i+1}")
        else:
            print(f"Failed to fetch data for chunk {i+1}")
    
    # Create a combined result
    if all_items:
        combined_data = {"data": {"items": all_items}}
        print(f"\nTotal items collected for {request_name}: {len(all_items)}")
        return combined_data
    else:
        print(f"\nNo items collected for {request_name}")
        return None


# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch OHLCV data from Birdeye API and save to CSV.")
    parser.add_argument("start_time", help="Start time in ISO 8601 format (e.g., '2025-04-13T18:00:00') or 'YYYY-MM-DD HH:MM:SS' format")
    parser.add_argument("end_time", help="End time in ISO 8601 format (e.g., '2025-04-13T19:00:00') or 'YYYY-MM-DD HH:MM:SS' format")
    parser.add_argument("--config", default="default_config.json", help="Path to the configuration file relative to the script.")
    parser.add_argument("--output-dir", default="output_csv", help="Directory to save CSV files, relative to the script location.")
    parser.add_argument("--token", help="Custom Solana token address to fetch data for.")
    parser.add_argument("--chunk-hours", type=int, default=24, help="Maximum hours per API request chunk (default: 24)")
    parser.add_argument("--rate-limit-sleep", type=float, default=1.0, help="Seconds to sleep between API requests (default: 1.0)")

    args = parser.parse_args()

    print("--- Script Start ---")

    # 1. Load API Key
    api_key = load_api_key()
    if not api_key:
        print("Exiting due to missing API key.")
        exit(1)

    # 2. Load Configuration
    config = load_config(args.config)
    if config is None:
        print("Exiting due to configuration error.")
        exit(1)
        
    # 3. Set token address if provided
    token_address = args.token
    if token_address:
        print(f"\nUsing custom token address: {token_address}")
        # Update the common parameters address too
        config["common_parameters"]["address"] = token_address
    else:
        token_address = config.get("common_parameters", {}).get("address")
        print(f"\nUsing default token address: {token_address}")

    # 4. Convert Times
    print(f"\nConverting times:")
    print(f"Input Start Time: {args.start_time}")
    print(f"Input End Time:   {args.end_time}")
    
    # Convert times to Unix timestamps
    start_unix = string_to_unix(args.start_time)
    end_unix = string_to_unix(args.end_time)
    
    if start_unix is None or end_unix is None:
        print("Exiting due to time conversion error.")
        exit(1)
        
    print(f"Converted Start Time (Unix): {start_unix}")
    print(f"Converted End Time (Unix):   {end_unix}")
    
    # Format unix timestamps as human-readable for reference
    start_human = datetime.fromtimestamp(start_unix, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    end_human = datetime.fromtimestamp(end_unix, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    print(f"Human-readable Start: {start_human}")
    print(f"Human-readable End:   {end_human}")

    # 5. Define Output Directory
    script_dir = os.path.dirname(__file__)
    output_csv_dir = os.path.join(script_dir, args.output_dir)
    print(f"\nOutput directory for CSVs: {output_csv_dir}")

    # 6. Split the time range into chunks if necessary
    time_chunks = chunk_time_range(start_unix, end_unix, args.chunk_hours)
    total_hours = (end_unix - start_unix) / 3600
    print(f"\nTotal time range: {total_hours:.2f} hours")
    print(f"Splitting into {len(time_chunks)} chunks of maximum {args.chunk_hours} hours each")
    
    # Display rate limit settings
    print(f"Rate limit sleep time between requests: {args.rate_limit_sleep} seconds")
    print(f"API limit: 60 requests per minute")

    # 7. Iterate through request configs, fetch data for all chunks, and save
    print("\n--- Fetching Data from Birdeye API & Saving ---")
    api_results = {}
    ohlcv_requests_config = config.get("ohlcv_requests", [])
    if not ohlcv_requests_config:
        print("Warning: No 'ohlcv_requests' found in the configuration file.")

    for request_conf in ohlcv_requests_config:
        request_name = request_conf.get("name", request_conf.get("endpoint", "unnamed_request"))
        
        # Use the new function to fetch and combine data from all chunks
        combined_data = fetch_and_combine_data(
            config, 
            request_conf, 
            time_chunks, 
            api_key, 
            token_address,
            args.rate_limit_sleep
        )
        
        if combined_data is not None:
            api_results[request_name] = combined_data
            print(f"Successfully fetched all data for {request_name}.")
            # Generate filename and save
            csv_filename = f"{request_name}.csv"
            save_to_csv(combined_data, csv_filename, output_csv_dir)
        else:
            print(f"Failed to fetch data for {request_name}. Skipping CSV save.")
            api_results[request_name] = None

        # Add a delay between different request types
        if request_conf != ohlcv_requests_config[-1]:  # If not the last request
            sleep_time = args.rate_limit_sleep * 2  # Double sleep time between different request types
            print(f"\nSleeping for {sleep_time} seconds before next request type...")
            time.sleep(sleep_time)

    print("\n--- Script End ---")
