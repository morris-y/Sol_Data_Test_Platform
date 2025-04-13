# 项目说明

本项目包含一个简单的 Flask Web 应用和一个用于从 Birdeye API 获取数据的 Python 脚本。

## Flask Web 应用 (`app.py`) 工作流程

### 当前工作流程（最新版本）

1. **启动应用**: 运行 `python app.py` 来启动 Flask 开发服务器。
2. **访问界面**: 在浏览器中打开 `http://127.0.0.1:5000` (或其他指定端口)。
3. **随机时间生成**: 应用会自动调用 `random_time_generator.py` 脚本生成一个随机的 24 小时时间段 (在最近 30 天内)。
4. **点击生成**: 用户点击 "Generate" 按钮。
5. **后端处理**:
   * SQL 文件生成:
     * 应用会根据 Solana Token 地址生成针对 `hubble.old_dex_ohlcv_hour` 和 `hubble.old_dex_ohlcv_min` 表的 SQL 查询文件
     * 生成的 SQL 文件保存在 `QA-20250411/DBeaver SQL/output_sql/` 目录下
   * Birdeye 脚本生成:
     * 应用会将 GMT+8 时间自动转换为 UTC (GMT+0) 时间
     * 生成一个用于调用 Birdeye API 的 Python 脚本，保存在 `QA-20250411/Birdeye/output_py/` 目录下
6. **结果展示**: 网页会跳转到结果页面，显示:
   * 用户选择的时间范围 (GMT+8)
   * 转换后的 UTC 时间范围
   * 生成的 SQL 文件路径
   * 生成的 Birdeye fetcher 脚本路径
   * "Fetch Birdeye Data" 按钮，用于调用 Birdeye API
7. **获取 Birdeye 数据**: 用户点击 "Fetch Birdeye Data" 按钮:
   * 应用会执行生成的 Python 脚本
   * 脚本会调用 `birdeye_fetcher.py` 获取指定时间范围内的 OHLCV 数据
   * 结果保存为 CSV 文件，位于 `QA-20250411/Birdeye/output_csv/` 目录下
   * 执行结果会显示在页面上，包括输出日志和任何错误信息

### 旧版工作流程（参考用）

当前 Web 应用的主要功能是根据用户选择的时间范围生成 SQL 查询文件。

1.  **启动应用**: 运行 `python app.py` 来启动 Flask 开发服务器。
2.  **访问界面**: 在浏览器中打开 `http://127.0.0.1:5000` (或其他指定端口)。
3.  **选择时间**: 用户在网页界面上选择查询的 **开始时间** 和 **结束时间**。
4.  **点击生成**: 用户点击 "Generate" 按钮。
5.  **后端处理**:
    *   `app.py` 中的 `/confirm` 路由接收到用户提交的开始和结束时间。
    *   脚本会查找预定义的 SQL 模板 (`sql_templates` 字典，包含 '1h' 和 '1m' 模板)。
    *   脚本会确保 `output_sql` 目录存在 (如果不存在则创建)。
    *   对于每个模板 ('1h', '1m')：
        *   脚本使用用户选择的开始和结束时间来格式化对应的 SQL 模板。
        *   格式化后的 SQL 查询语句被写入到 `output_sql` 目录下的相应 `.sql` 文件中 (例如: `query_1h.sql`, `query_1m.sql`)。
6.  **结果展示**: 网页会跳转到结果页面，显示用户选择的时间范围以及刚刚生成的 SQL 文件的路径。

## Birdeye 数据获取脚本 (`QA-20250411/Birdeye/birdeye_fetcher.py`)

该脚本用于从 Birdeye API 获取 OHLCV 数据并保存为 CSV 文件。

*   **手动运行方式**: 在命令行中切换到 `QA-20250411/Birdeye/` 目录，然后执行：
    ```bash
    python birdeye_fetcher.py "YYYY-MM-DD HH:MM:SS" "YYYY-MM-DD HH:MM:SS"
    ```
    (请将时间替换为实际的格式时间，格式为 `YYYY-MM-DD HH:MM:SS`)。

*   **通过 Web 应用运行**: 使用 Web 应用生成并执行 Birdeye fetcher 脚本：
    1. 访问 Web 应用并生成 SQL 和 Birdeye 脚本
    2. 在结果页面点击 "Fetch Birdeye Data" 按钮
    3. 查看执行结果，数据将被保存在 `QA-20250411/Birdeye/output_csv/` 目录下

*   **功能**:
    *   读取 `.env` 文件中的 Birdeye API 密钥。
    *   读取 `default_config.json` 中的 API 请求配置。
    *   根据命令行传入的开始和结束时间调用 Birdeye API (获取 1m 和 1H 数据)。
    *   将获取到的数据分别保存到 `output_csv` 目录下的 CSV 文件中 (例如: `1m_interval_request.csv`, `1H_interval_request.csv`)。
