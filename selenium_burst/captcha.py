# Pillow 11+ 兼容补丁：为移除的常量提供别名，避免第三方库引用失败
try:
    import PIL
    import PIL.Image as _PIL_Image

    # Pillow>=10 删除了这些常量，使用 Resampling 枚举替代
    if not hasattr(_PIL_Image, 'ANTIALIAS'):
        try:
            from PIL.Image import Resampling as _Resampling

            _PIL_Image.ANTIALIAS = _Resampling.LANCZOS
            _PIL_Image.BICUBIC = _Resampling.BICUBIC
            _PIL_Image.BILINEAR = _Resampling.BILINEAR
        except Exception:
            pass
except Exception:
    pass

import random
import ddddocr
import requests
from selenium.webdriver.common.by import By
from config import CAPTCHA_DIRECT_URL, LOGIN_URL, REQUEST_TIMEOUT


class SimpleCaptchaRecognizer:
    """简单的验证码识别器"""

    def __init__(self):
        """初始化OCR引擎与HTTP会话"""
        try:
            self.ocr = ddddocr.DdddOcr()
            print("✅ 验证码识别引擎初始化成功")
        except Exception as e:
            print(f"❌ 验证码识别引擎初始化失败: {e}")
            self.ocr = None
        # 复用HTTP会话，减少TLS握手；优先通过接口获取验证码
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': "LOGIN_URL",
        })

    def get_captcha_image(self, cookies: dict | None = None):
        """获取验证码图片（可传入浏览器cookies以保持同一会话）"""
        try:
            if cookies:
                # 覆盖为当前会话的cookies
                self.session.cookies.clear()
                self.session.cookies.update(cookies)
            # 加上 time 参数触发服务端生成新验证码
            params = {"time": f"{random.random():.16f}"}
            response = self.session.get(
                CAPTCHA_DIRECT_URL,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            if response.status_code == 200:
                return response.content
            else:
                return None
        except Exception:
            return None

    def get_captcha_image_from_browser(self, browser):
        """通过浏览器直接截图验证码元素，作为网络失败的回退方案"""
        try:
            img_elem = browser.find_element(By.XPATH, "//img[contains(@src,'captcha.jsp')]")
            return img_elem.screenshot_as_png
        except Exception:
            return None

    def recognize_captcha(self, img_bytes: bytes | None = None, cookies: dict | None = None, browser=None):
        """识别验证码（优先HTTP接口，失败再回退浏览器截图）"""
        if self.ocr is None:
            return None
        try:
            # 如果没有提供图片，则优先HTTP拉取，失败时回退到浏览器截图
            if img_bytes is None:
                img_bytes = self.get_captcha_image(cookies=cookies)
                if img_bytes is None and browser is not None:
                    img_bytes = self.get_captcha_image_from_browser(browser)
                if img_bytes is None:
                    return None
            # 识别
            result = self.ocr.classification(img_bytes)
            return result
        except Exception:
            return None

    def recognize_math_captcha(self, img_bytes: bytes | None = None, cookies: dict | None = None, browser=None):
        """识别算术验证码（优先HTTP接口，失败再回退浏览器截图）"""
        if self.ocr is None:
            return None
        try:
            if img_bytes is None:
                img_bytes = self.get_captcha_image(cookies=cookies)
                if img_bytes is None and browser is not None:
                    img_bytes = self.get_captcha_image_from_browser(browser)
                if img_bytes is None:
                    return None
            result = self.ocr.classification(img_bytes)
            result = result.replace("=", "").replace("?", "").strip()
            # 简单四则运算
            for op in ['+', '-', '*', 'x', '/']:
                if op in result:
                    a, b = result.split(op, 1)
                    try:
                        if op == '+':
                            return str(int(a) + int(b))
                        if op == '-':
                            return str(int(a) - int(b))
                        if op in ['*', 'x']:
                            return str(int(a) * int(b))
                        if op == '/':
                            return str(int(int(a) / int(b)))
                    except Exception:
                        break
            return result
        except Exception:
            return None


# 全局实例
captcha_recognizer = SimpleCaptchaRecognizer()


def recognize_captcha_direct(cookies: dict | None = None, browser=None):
    """直接识别验证码（兼容原接口）"""
    return captcha_recognizer.recognize_captcha(cookies=cookies, browser=browser)


def recognize_math_captcha_direct(cookies: dict | None = None, browser=None):
    """直接识别算术验证码（兼容原接口）"""
    return captcha_recognizer.recognize_math_captcha(cookies=cookies, browser=browser)
