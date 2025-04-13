import json
import os
import sys
from datetime import datetime, timezone
import argparse
import requests
import time
import pandas as pd
import math

# === Utility Functions ===

def string_to_unix(time_str):
    """Convert a string time in format 'YYYY-MM-DD HH:MM:SS' to Unix timestamp"""
    try:
        # Parse the string time and assume it's in UTC
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        # Set the timezone to UTC explicitly
        dt = dt.replace(tzinfo=timezone.utc)
        # Convert to Unix timestamp (seconds since epoch)
        unix_time = int(dt.timestamp())
        return unix_time
    except Exception as e:
        print(f"Error converting time string to Unix timestamp: {e}")
        sys.exit(1)

def load_api_key():
    """Loads the Birdeye API key from the .env file."""
    try:
        from dotenv import load_dotenv
        # Get the directory of this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up to the Birdeye directory
        birdeye_dir = os.path.dirname(script_dir)
        # Path to the .env file
        dotenv_path = os.path.join(birdeye_dir, '.env')
        # Load the .env file
        load_dotenv(dotenv_path=dotenv_path)
        # Get the API key
        api_key = os.getenv("BIRDEYE_API_KEY")
        if not api_key or api_key == "YOUR_API_KEY_HERE":
            print("Error: BIRDEYE_API_KEY not found or not set in .env file.")
            print(f"Please create or update {dotenv_path}")
            return None
        print("API Key loaded successfully.")
        return api_key
    except Exception as e:
        print(f"Error loading API key: {e}")
        return None

def load_config(config_path=None):
    """Loads the configuration file."""
    try:
        # Get the directory of this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up to the Birdeye directory
        birdeye_dir = os.path.dirname(script_dir)
        # Default config path
        if config_path is None:
            config_path = os.path.join(birdeye_dir, "default_config.json")
        else:
            # If config_path is not absolute, make it relative to birdeye_dir
            if not os.path.isabs(config_path):
                config_path = os.path.join(birdeye_dir, config_path)
        
        # Load the config file
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"Configuration loaded successfully from {config_path}\n")
        return config
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return None

def chunk_time_range(start_unix, end_unix, chunk_hours=24):
    """Split a time range into chunks of specified hours."""
    if chunk_hours <= 0:
        chunk_hours = 24
    
    # Calculate total duration and chunk size in seconds
    total_duration = end_unix - start_unix
    chunk_size = chunk_hours * 3600
    
    # Calculate number of chunks needed
    num_chunks = math.ceil(total_duration / chunk_size)
    
    # Create chunks
    chunks = []
    for i in range(num_chunks):
        chunk_start = start_unix + i * chunk_size
        # Make sure the last chunk doesn't exceed end_unix
        chunk_end = min(start_unix + (i + 1) * chunk_size - 1, end_unix)
        chunks.append((chunk_start, chunk_end))
    
    return chunks

def save_to_csv(data, filename, output_dir):
    """Save data to a CSV file."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Full path to output file
        output_path = os.path.join(output_dir, filename)
        
        # Check if data is valid
        if not data or not isinstance(data, list) or len(data) == 0:
            print(f"No data to save for {filename}.")
            return False
        
        # Check what kind of data structure we're dealing with
        first_item = data[0]
        
        if isinstance(first_item, dict):
            # Convert list of dicts to DataFrame
            df = pd.DataFrame(data)
            # Save to CSV
            df.to_csv(output_path, index=False)
            print(f"Saved {len(data)} records to {output_path}")
            return True
            
        elif isinstance(first_item, list):
            # If it's a list of lists, convert to DataFrame with default column names
            df = pd.DataFrame(data)
            # Save to CSV
            df.to_csv(output_path, index=False)
            print(f"Saved {len(data)} records to {output_path}")
            return True
            
        else:
            print(f"Unsupported data structure for {filename}. Expected list of dicts or list of lists.")
            return False
            
    except Exception as e:
        print(f"Error saving data to CSV: {e}")
        return False

def fetch_ohlcv_data(config, request_config, start_unix, end_unix, api_key, token_address=None):
    """Fetch OHLCV data from Birdeye API."""
    try:
        # Get the base URL
        base_url = config.get("common_parameters", {}).get("base_url")
        if not base_url:
            print("Error: base_url not found in configuration.")
            return None
            
        # Prepare endpoints
        endpoints = config.get("endpoints", {})
        ohlcv_endpoint = endpoints.get("ohlcv", "")
        url = f"{base_url}{ohlcv_endpoint}"
        
        # Prepare headers
        common_headers = config.get("common_parameters", {}).get("headers", {})
        api_key_header = common_headers.get("api_key_header", "x-api-key")
        headers = {
            api_key_header: api_key,
            "accept": "application/json",
            "x-chain": "solana"  
        }
        
        # Prepare query parameters
        query_params = {}
        # Add parameters from request config
        for param_name, param_value in request_config.get("parameters", {}).items():
            query_params[param_name] = param_value
        
        # Add time range parameters
        query_params["time_from"] = start_unix
        query_params["time_to"] = end_unix
        
        # Add token address if provided
        if token_address:
            print(f"Using custom token address: {token_address}\n")
            query_params["address"] = token_address
            
        # Make the request
        print(f"Attempting API call for: {request_config['name']}")
        print(f"URL: {url}")
        print(f"Params: {query_params}")
        
        response = requests.get(url, headers=headers, params=query_params)
        
        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            if data.get("success", False):
                if "items" in data.get("data", {}):
                    return data["data"]["items"]  
                else:
                    return data.get("data", [])  
            else:
                print(f"API returned error for {request_config['name']}: {data.get('message', 'Unknown error')}")
                return None
        else:
            print(f"HTTP error occurred for {request_config['name']}: {response.status_code} {response.reason} for url: {response.url} (Status: {response.status_code})")
            print(f"Response Body: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error fetching OHLCV data: {e}")
        return None

def fetch_and_combine_data(config, request_config, chunks, api_key, token_address=None, rate_limit_sleep=1.0):
    """Fetch data for all chunks and combine the results."""
    # Store all fetched items
    all_items = []
    
    # Process each chunk
    num_chunks = len(chunks)
    for i, (chunk_start, chunk_end) in enumerate(chunks):
        print(f"\nChunk {i+1}/{num_chunks}: {datetime.fromtimestamp(chunk_start, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} to {datetime.fromtimestamp(chunk_end, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Add delay for rate limiting (except for the first request)
        if i > 0:
            print(f"Sleeping for {rate_limit_sleep} seconds to respect API rate limits...")
            time.sleep(rate_limit_sleep)
        
        # Fetch data for this chunk
        chunk_data = fetch_ohlcv_data(config, request_config, chunk_start, chunk_end, api_key, token_address)
        
        # Check if fetch was successful
        if chunk_data and isinstance(chunk_data, list):
            print(f"Successfully fetched {len(chunk_data)} records for chunk {i+1}")
            all_items.extend(chunk_data)
        else:
            print(f"Failed to fetch data for chunk {i+1}")
    
    # Return combined data
    if all_items:
        print(f"\nTotal records collected for {request_config['name']}: {len(all_items)}")
        return all_items
    else:
        print(f"\nNo items collected for {request_config['name']}")
        return None

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Fetch OHLCV data from Birdeye API.")
    parser.add_argument("start_time", help="Start time in format 'YYYY-MM-DD HH:MM:SS' (UTC)")
    parser.add_argument("end_time", help="End time in format 'YYYY-MM-DD HH:MM:SS' (UTC)")
    parser.add_argument("--token", dest="token_address", default="__TOKEN_ADDRESS__", 
                        help="Token address to fetch data for")
    parser.add_argument("--config", dest="config_path", default=None,
                        help="Path to config file")
    parser.add_argument("--chunk-hours", dest="chunk_hours", type=int, default=24,
                        help="Maximum hours per chunk when splitting requests")
    parser.add_argument("--rate-limit-sleep", dest="rate_limit_sleep", type=float, default=1.0,
                        help="Sleep time between API requests in seconds")
    parser.add_argument("--output-dir", dest="output_dir", default=None,
                        help="Directory to save output CSV files")
    
    args = parser.parse_args()
    
    print("--- Script Start ---")
    
    # Load the API key
    api_key = load_api_key()
    if not api_key:
        sys.exit(1)
    
    # Load the configuration
    config = load_config(args.config_path)
    if not config:
        sys.exit(1)
    
    # Set output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        # Get the directory of this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up to the Birdeye directory
        birdeye_dir = os.path.dirname(script_dir)
        # Default output directory
        output_dir = os.path.join(birdeye_dir, "output_csv")
    
    print(f"\nConverting times:")
    print(f"Input Start Time: {args.start_time}")
    print(f"Input End Time:   {args.end_time}")
    
    # Convert string times to Unix timestamps
    start_unix = string_to_unix(args.start_time)
    end_unix = string_to_unix(args.end_time)
    
    print(f"Converted Start Time (Unix): {start_unix}")
    print(f"Converted End Time (Unix):   {end_unix}")
    print(f"Human-readable Start: {datetime.fromtimestamp(start_unix, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"Human-readable End:   {datetime.fromtimestamp(end_unix, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    print(f"\nOutput directory for CSVs: {output_dir}")
    
    # Calculate time range in hours
    hours_diff = (end_unix - start_unix) / 3600
    print(f"\nTotal time range: {hours_diff:.2f} hours")
    
    # Chunk the time range
    chunks = chunk_time_range(start_unix, end_unix, args.chunk_hours)
    print(f"Splitting into {len(chunks)} chunks of maximum {args.chunk_hours} hours each")
    print(f"Rate limit sleep time between requests: {args.rate_limit_sleep} seconds")
    print(f"API limit: 60 requests per minute")
    
    print("\n--- Fetching Data from Birdeye API & Saving ---")
    
    # Get the request configurations
    request_configs = config.get("request_configs", [])
    
    # Fetch and save data for each request configuration
    for request_config in request_configs:
        config_name = request_config.get("name", "unknown")
        csv_filename = f"{config_name}.csv"
        
        print(f"\nFetching data for {config_name} in {len(chunks)} chunks:")
        
        # Fetch and combine data from all chunks
        combined_data = fetch_and_combine_data(
            config, 
            request_config, 
            chunks, 
            api_key, 
            args.token_address,
            args.rate_limit_sleep
        )
        
        # Save to CSV if data was fetched
        if combined_data:
            save_success = save_to_csv(combined_data, csv_filename, output_dir)
            if save_success:
                print(f"Successfully saved {config_name} data to {os.path.join(output_dir, csv_filename)}")
            else:
                print(f"Failed to save {config_name} data to CSV.")
        else:
            print(f"Failed to fetch data for {config_name}. Skipping CSV save.")
        
        # Add delay between different request types
        if request_config != request_configs[-1]:
            sleep_time = args.rate_limit_sleep * 2  # Longer sleep between different request types
            print(f"\nSleeping for {sleep_time} seconds before next request type...")
            time.sleep(sleep_time)

if __name__ == "__main__":
    # The time range to fetch (UTC/GMT+0)
    start_time = "__START_TIME__"
    end_time = "__END_TIME__"
    token_address = "__TOKEN_ADDRESS__"  # Solana token address
    
    print(f"Fetching Birdeye data for time range (UTC):")
    print(f"Start: {start_time}")
    print(f"End: {end_time}")
    print(f"Token: {token_address}")
    
    # Pass the command line arguments to the main function
    sys.argv = ["birdeye_fetch.py", start_time, end_time, "--token", token_address]
    main()
