# **TheHive Qradar Integration**

## **Overview**
This project is a modified and enhanced version of an existing integration between **IBM QRadar** and **TheHive**. It automates the process of fetching offenses from QRadar, converting them into alerts, and importing them into TheHive. Additionally, it provides a structured configuration setup and a modular approach for seamless integration.

The core functionality is handled by **smart_cloner.py**, which runs as a scheduled service every hour. The configuration settings, including API keys and URLs, are stored in **conf/smartclonner.conf**. The project also includes connectors for **QRadar** and **TheHive**, ensuring efficient communication between these platforms.

## **How It Works**
1. **Fetching QRadar Offenses**: The script retrieves offenses from QRadar using its API.
2. **Processing and Conversion**: The offenses are processed and formatted as TheHive alerts.
3. **Alert Creation in TheHive**: The alerts are pushed to TheHive for further analysis and incident response.
4. **Scheduled Execution**: The script is designed to run as a service every hour, ensuring continuous monitoring and alert generation.

## **Installation & Configuration**

### **1. Update Configuration File and install dependency *
Modify the **conf/smartclonner.conf** file with your environment-specific values:

#### **Install Dependencies:**
Make sure you have the required Python libraries:

```bash
pip install Requirement.txt
```

#### **TheHive Configuration:**
```ini
[TheHive]
url = http://your-thehive-instance:9000
user = your-username
api_key = your-api-key
```

#### **QRadar Configuration:**
```ini
[QRadar]
server = your-qradar-server-ip
auth_token = your-qradar-api-token
```

### **2. Running the Script**
You can execute the script manually or set it up as a scheduled job:

#### **Manual Execution:**
```bash
python3 smart_clonner.py
```

#### **Scheduled Execution (Crontab Example - Every Hour):**
```bash
0 * * * * /usr/bin/python3 /path/to/smart_clonner.py
```

```service
systemctl daemon-reload
sudo systemctl enable thehive-qradar.service
sudo systemctl start thehive-qradar.service
sudo systemctl enable thehive-qradar.timer
sudo systemctl start thehive-qradar.timer
```

## **Project Structure**
```
├── conf/
│   ├── smartclonner.conf      # Configuration file (API keys, URLs, etc.)
├── objects/
│   ├── offense2alert.py       # Convert offence to thehive alert
│   ├── qradar_connector.py    # Connectors for  QRadar
│   ├── thehive_connector.py   # Connectors for TheHive 
├── smart_cloner.py            # Main script to fetch and process offenses
├── thehive-qradar.service     # service
├── thehive-qradar.timer       # service timer
├── README.md                  # Project documentation
```

## **Differences from the Original Project**
This project is a fork of [Pierre Barlet’s qradar2thehive](https://github.com/pierrebarlet/qradar2thehive) with some modifications:
✅ **Service-Based Execution**: Designed to run as a scheduled service every hour for continuous operation.

## **Future Enhancements**
- Support for additional alert customization and filtering.
- Web-based UI for configuration management.

