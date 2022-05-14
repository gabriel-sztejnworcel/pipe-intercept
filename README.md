# pipe-intercept
#### Intercept Windows Named Pipes communication using Burp or similar HTTP proxy tools
Named Pipes is a very popular mechanism for interprocess communication on Windows. They are used in many application, including Windows Remote Procedure Call (RPC). The purpose of this tool is to allow security researchers and pentesters to perform security assessment for application that use named pipes.
This project is heavily inspired by the great [MITM_Intercept](https://github.com/cyberark/MITM_Intercept) project from CyberArk Labs.
### How Does it Work?
The tool creates a client/server pipe proxy with a WebSocket client/server bridge. The WebSocket client connects to the WebSocket server through a proxy such as Burp.
