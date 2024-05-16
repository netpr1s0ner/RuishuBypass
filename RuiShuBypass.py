import os
from DrissionPage import ChromiumOptions, WebPage
import socket


option = ChromiumOptions()  # 重置浏览器配置
option.headless(False)
option.set_argument("--disable-gpu")
option.set_argument("--allow-running-insecure-content")
option.set_argument("--disable-infobars")
option.set_argument("--log-level=3")
webpage = WebPage(mode='d', chromium_options=option)

def parse_http_request(request):
    """
    Parse the HTTP request and return method, URL, headers, and data.
    """
    headers = {}
    lines = request.split('\r\n')

    # Parse request line
    request_line = lines[0].split(' ')
    method = request_line[0]
    url = request_line[1]
    http_version = request_line[2]

    # Parse headers
    for line in lines[1:]:
        if line == "":
            break
        key, value = line.split(': ', 1)
        headers[key] = value

    # Parse data
    data_index = request.find("\r\n\r\n")
    if data_index != -1:
        data = request[data_index + 4:]
    else:
        data = ""

    return method, url, headers, data

def open_basic_url(url):
    if not webpage.get(url, retry=0):
        print("[-] ChromeBrowser 启动失败")
        os.exit(0)

def view_in_browser(url, headers={}, data="", method="GET"):
    try:
        body = ""
        if method != "GET":
            if 'Content-Type' not in headers:
                headers['Content-Type'] = 'application/x-www-form-urlencoded'

            if len(data) > 0:
                body = f"body: '{data}',"

        javaScriptCookie = ""
        if 'Cookie' in headers:  # 设置cookie
            for cookie in headers['Cookie'].split("; "):
                javaScriptCookie += f"document.cookie = '{cookie}';\n"
        javaScript = f"""return (async () => {{
      {javaScriptCookie}
      var result = '';
      try {{
        let response = await fetch('{url}', {{
          method: '{method}',
          headers: {headers},
          {body}
        }});

        result = "HTTP/1.1 " + response.status + " " + response.statusText + "\\n";

        // 处理headers
        var headersStringPre = "";
        var headersString = "";
        var headersStringSub= "";
        response.headers.forEach((value, key) => {{
          
          headersString += key + ": " + value + "\\n";
        }});

        // 将状态码、headers字符串和body字符串结合
        let body = await response.text();
        result = result + headersString + "content-length: " + body.length + "\\n\\n" + body;
        return result;

      }} catch (error) {{
        console.log('Network request failed with message: ', error.message);
        return result;
      }}
    }})()"""
        result = webpage.run_js(javaScript, timeout=5)
        print(result)
        return result

    except:
        return ""


if __name__ == '__main__':
    listenPort = 8050  # 设置本地监听地址  端口转发 转发所有数据到目标IP
    basicUrl = "https://cas.sbj.cnipa.gov.cn"  # basic路径 目标站点根路径
    basicUrl = basicUrl.strip("/")

    initUrl = basicUrl + "/cas/login?service=https://wcjs.sbj.cnipa.gov.cn/cas/login"  # 触发 瑞数js的任意路径
    open_basic_url(initUrl)


    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(("0.0.0.0", listenPort))
        server_socket.listen(5)
        print(f"Listening on 0.0.0.0:{listenPort}...")

        # 监听
        while True:
            client_socket, client_address = server_socket.accept()
            with client_socket:
                print(f"Connection from {client_address}")
                request = client_socket.recv(65000).decode('utf-8')
                if request.startswith('GET') or request.startswith('POST'):
                    method, path, headers, data = parse_http_request(request)
                    currentUrl = basicUrl + path
                    client_socket.sendall(view_in_browser(currentUrl,headers,data,method=method).encode("utf-8"))
                else:
                    client_socket.sendall("Received non-HTTP request".encode("utf-8"))
                client_socket.close()