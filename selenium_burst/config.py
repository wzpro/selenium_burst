# config.py
# 配置文件

# 登录页面URL
LOGIN_URL = "https://www.baidu.com"

# 固定用户名
USERNAME = "test"

# 密码字典文件
PASSWORD_FILE = "passwords.txt"

# 验证码直接接口URL
CAPTCHA_DIRECT_URL = "https://www.baidu.com/captcha.jsp"

# 浏览器驱动路径
DRIVER_PATH = "D:\Desktop\/newx\\reset_py\pc\chromedriver-win64\chromedriver.exe"

# 超时设置
TIMEOUT = 5                 # 页面元素等待（秒）
REQUEST_TIMEOUT = 2         # 获取验证码HTTP超时（秒）


# 性能优化
HEADLESS = False            # 关闭无头，显示浏览器窗口