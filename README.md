# pipe-intercept
#### Intercept Windows Named Pipes communication using Burp or similar HTTP proxy tools
Named Pipes are very popular for interprocess communication on Windows. They are used in many application, including Windows Remote Procedure Call (RPC). The purpose of this tool is to allow security researchers and pentesters to perform security assessment for application that use named pipes.
This project is inspired by the great [MITM_Intercept](https://github.com/cyberark/MITM_Intercept) project from CyberArk Labs.
### How Does it Work?
The tool creates a client/server pipe proxy with a WebSocket client/server bridge. The WebSocket client connects to the WebSocket server through a proxy such as Burp.

Flow diagram:

![Flow Diagram](images/pipe-intercept.png)
### Usage
```
usage: pipe_intercept.py [-h] --pipe-name PIPE_NAME --ws-port WS_PORT --http-proxy-port HTTP_PROXY_PORT [--log-level {CRITICAL,ERROR,WARNING,INFO,DEBUG}]

options:
  -h, --help            show this help message and exit
  --pipe-name PIPE_NAME
  --ws-port WS_PORT
  --http-proxy-port HTTP_PROXY_PORT
  --log-level {CRITICAL,ERROR,WARNING,INFO,DEBUG}
```
### Example
Docker on Windows uses a named pipe to communicate between the client and the docker service. The pipe name is "\\\\.\pipe\docker_engine". Let's see how we can intercept this communication. We start by running the tool:
```
C:\pipe-intercept>python pipe_intercept.py --pipe-name docker_engine --ws-port 8888 --http-proxy-port 8080

INFO:websockets.server:server listening on 0.0.0.0:8888
INFO:websockets.server:server listening on [::]:8888
```
Now we can start Burp, and from another shell create a Windows container:
```
C:\pipe-intercept>docker run -it --name win mcr.microsoft.com/windows:1809-amd64 cmd

Microsoft Windows [Version 10.0.17763.2803]
(c) 2018 Microsoft Corporation. All rights reserved.

C:\>dir
 Volume in drive C has no label.
 Volume Serial Number is 5C09-8FFA

 Directory of C:\

05/07/2020  06:16 AM             5,510 License.txt
04/04/2022  02:57 PM    <DIR>          PerfLogs
04/04/2022  04:13 PM    <DIR>          Program Files
04/04/2022  02:57 PM    <DIR>          Program Files (x86)
04/04/2022  04:17 PM    <DIR>          Users
04/04/2022  04:13 PM    <DIR>          Windows
               1 File(s)          5,510 bytes
               5 Dir(s)  21,188,812,800 bytes free

C:\>
```
Now if we open the WebSocket tab in Burp, we can see the communication:

![Burp WebSocket History](images/burp_ws_history.png)

We can also turn interception on and change the message:

![Burp Intercept](images/burp_intercept.png)

```
Microsoft Windows [Version 10.0.17763.2803]
(c) 2018 Microsoft Corporation. All rights reserved.

C:\>dir
 Volume in drive C has no label.
 Volume Serial Number is 5C09-8FFA

 Directory of C:\

05/07/2020  06:16 AM             5,510 License.txt
04/04/2022  02:57 PM    <DIR>          PerfLogs
04/04/2022  04:13 PM    <DIR>          Modified Name
04/04/2022  02:57 PM    <DIR>          Program Files (x86)
04/04/2022  04:17 PM    <DIR>          Users
04/04/2022  04:13 PM    <DIR>          Windows
               1 File(s)          5,510 bytes
               5 Dir(s)  21,188,288,512 bytes free

C:\>
```
### Important Note
This tool should not be used in production systems as it might break the target application. For example, the application might find a pipe server instance with its own name and fail to start.
