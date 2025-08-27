import time
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, date
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

class CFETSScheduledSpider:
    def __init__(self):
        self.url = "https://www.cfets-nex.com.cn/Market/marketData/money"
        self.today_data = {}
        self.target_email = "ichenry@qq.com"

        # Initialize email config with placeholder values, to be populated by the workflow
        self.email_config = {
            'smtp_server': '',
            'smtp_port': 587,
            'sender_email': '',
            'sender_password': '',
        }

    def setup_driver(self):
        """设置Chrome浏览器驱动"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument(
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver

    def get_sentiment_data(self):
        """获取情绪指数数据"""
        driver = None
        try:
            current_time = datetime.now().strftime("%H:%M")
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始获取数据...")

            driver = self.setup_driver()
            driver.get(self.url)

            # 等待图表加载
            wait = WebDriverWait(driver, 30)
            wait.until(EC.presence_of_element_located((By.ID, "FXSIChart")))
            time.sleep(5)

            # 获取ECharts数据
            indices = self.extract_indices(driver)

            if indices and len(indices) >= 4:
                # 保存数据
                today_str = date.today().strftime("%Y-%m-%d")
                if today_str not in self.today_data:
                    self.today_data[today_str] = {}

                self.today_data[today_str][current_time] = indices[:4]

                print(f"[{current_time}] 成功获取: {indices[:4]}")
                print("指数含义: [大行资金面, 中小行资金面, 非银机构资金面, 综合指数]")
                self.save_data()
                return indices[:4]
            else:
                print(f"[{current_time}] 获取数据失败")
                return None

        except Exception as e:
            print(f"获取数据异常: {e}")
            return None
        finally:
            if driver:
                driver.quit()

    def extract_indices(self, driver):
        """提取4个指数值"""
        try:
            # 获取ECharts配置
            script = """
            var chart = echarts.getInstanceByDom(document.getElementById('FXSIChart'));
            if (chart && chart.getOption) {
                var option = chart.getOption();
                if (option && option.series && option.series[0] && option.series[0].data) {
                    return option.series[0].data[option.series[0].data.length - 1];
                }
            }
            return null;
            """

            latest_data = driver.execute_script(script)

            if latest_data and isinstance(latest_data, dict):
                if 'single' in latest_data and 'value' in latest_data:
                    single_values = latest_data['single']
                    combined_value = latest_data['value']

                    if isinstance(single_values, list) and len(single_values) >= 3:
                        return [single_values[0], single_values[1], single_values[2], combined_value]

            return None

        except Exception as e:
            print(f"提取数据失败: {e}")
            return None

    def save_data(self):
        """保存数据到文件"""
        try:
            filename = f"sentiment_data_{date.today().strftime('%Y%m%d')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.today_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存失败: {e}")

    def generate_email_content(self, is_summary=False):
        """生成邮件内容"""
        today_str = date.today().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M:%S")

        if is_summary:
            subject = f"CFETS情绪指数日报 - {today_str}"
            body = f"CFETS情绪指数日报\n日期: {today_str}\n\n"
        else:
            subject = f"CFETS情绪指数更新 - {today_str} {current_time}"
            body = f"CFETS情绪指数更新\n时间: {today_str} {current_time}\n\n"

        if today_str in self.today_data:
            body += "指数数据:\n"
            body += "-" * 60 + "\n"
            body += f"{'时间':<8} {'大行':<8} {'中小行':<8} {'非银':<8} {'综合':<8}\n"
            body += "-" * 60 + "\n"

            for time_point, values in self.today_data[today_str].items():
                if len(values) >= 4:
                    body += f"{time_point:<8} {values[0]:<8.2f} {values[1]:<8.2f} {values[2]:<8.2f} {values[3]:<8.2f}\n"

            body += "-" * 60 + "\n"
            body += "\n指数含义:\n"
            body += "- 大行: 大型银行资金面情绪指数\n"
            body += "- 中小行: 中小银行资金面情绪指数\n"
            body += "- 非银: 非银机构资金面情绪指数\n"
            body += "- 综合: 综合情绪指数\n"
        else:
            body += "暂无数据"

        return subject, body

    def send_email(self, subject, body, attach_file=None):
        """发送邮件"""
        try:
            # 检查邮件配置
            if not self.email_config['sender_email'] or not self.email_config['sender_password']:
                print("邮件配置不完整，请设置发送邮箱和授权码")
                return False

            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = self.email_config['sender_email']
            msg['To'] = self.target_email
            msg['Subject'] = subject

            # 添加邮件正文
            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # 添加附件
            if attach_file:
                try:
                    with open(attach_file, "rb") as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {attach_file}',
                        )
                    msg.attach(part)
                except Exception as e:
                    print(f"添加附件失败: {e}")

            # 发送邮件
            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['sender_email'], self.email_config['sender_password'])
            text = msg.as_string()
            server.sendmail(self.email_config['sender_email'], self.target_email, text)
            server.quit()

            print(f"邮件发送成功: {subject}")
            return True

        except Exception as e:
            print(f"邮件发送失败: {e}")
            return False

    def print_summary(self):
        """打印数据汇总"""
        today_str = date.today().strftime("%Y-%m-%d")
        if today_str in self.today_data:
            print(f"\n今日数据汇总 ({today_str}):")
            print("-" * 60)
            print(f"{'时间':<8} {'大行':<6} {'中小行':<6} {'非银':<6} {'综合':<6}")
            print("-" * 60)
            for time_point, values in self.today_data[today_str].items():
                if len(values) >= 4:
                    print(f"{time_point:<8} {values[0]:<6} {values[1]:<6} {values[2]:<6} {values[3]:<6}")
            print("-" * 60)

    def job_0846(self):
        """08:46 任务"""
        print("\n执行 08:46 任务")
        result = self.get_sentiment_data()
        if result:
            self.print_summary()
            # 发送更新邮件
            subject, body = self.generate_email_content()
            self.send_email(subject, body)

    def job_1016(self):
        """10:16 任务"""
        print("\n执行 10:16 任务")
        result = self.get_sentiment_data()
        if result:
            self.print_summary()
            # 发送更新邮件
            subject, body = self.generate_email_content()
            self.send_email(subject, body)

    def job_1431(self):
        """14:31 任务"""
        print("\n执行 14:31 任务")
        result = self.get_sentiment_data()
        if result:
            self.print_summary()
            # 发送更新邮件
            subject, body = self.generate_email_content()
            self.send_email(subject, body)

    def job_1601(self):
        """16:01 任务 - 发送日报"""
        print("\n执行 16:01 任务")
        result = self.get_sentiment_data()
        if result:
            self.print_summary()
            # 发送日报邮件（带附件）
            subject, body = self.generate_email_content(is_summary=True)
            filename = f"sentiment_data_{date.today().strftime('%Y%m%d')}.json"
            self.send_email(subject, body, filename)

    def setup_email_config(self, sender_email, sender_password, smtp_server='smtp.qq.com', smtp_port=587):
        """设置邮件配置"""
        self.email_config.update({
            'sender_email': sender_email,
            'sender_password': sender_password,
            'smtp_server': smtp_server,
            'smtp_port': smtp_port
        })
        print("邮件配置已更新")

    def test_now(self):
        """测试模式"""
        print("测试模式 - 获取当前数据")
        result = self.get_sentiment_data()
        if result:
            self.print_summary()
            # 发送测试邮件
            subject, body = self.generate_email_content()
            self.send_email(f"[测试] {subject}", body)
        return result


