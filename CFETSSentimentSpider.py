import time
import json
import schedule
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
        self.get_sentiment_data()
        self.print_summary()

    def job_1016(self):
        """10:16 任务"""
        print("\n执行 10:16 任务")
        self.get_sentiment_data()
        self.print_summary()

    def job_1431(self):
        """14:31 任务"""
        print("\n执行 14:31 任务")
        self.get_sentiment_data()
        self.print_summary()

    def job_1601(self):
        """16:01 任务"""
        print("\n执行 16:01 任务")
        self.get_sentiment_data()
        self.print_summary()

    def setup_schedule(self):
        """设置定时任务"""
        schedule.clear()
        schedule.every().day.at("08:46").do(self.job_0846)
        schedule.every().day.at("10:16").do(self.job_1016)
        schedule.every().day.at("14:31").do(self.job_1431)
        schedule.every().day.at("16:01").do(self.job_1601)

        print("定时任务已设置: 08:46, 10:16, 14:31, 16:01")

    def run_scheduled(self):
        """运行定时任务"""
        self.setup_schedule()
        print(f"\n定时爬虫启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            while True:
                schedule.run_pending()
                time.sleep(30)
        except KeyboardInterrupt:
            print("\n定时任务已停止")

    def test_now(self):
        """测试模式"""
        print("测试模式 - 获取当前数据")
        result = self.get_sentiment_data()
        if result:
            self.print_summary()
        return result


if __name__ == "__main__":
    spider = CFETSScheduledSpider()

    # 测试模式
    spider.test_now()

    # 定时模式 - 取消注释启用
    # spider.run_scheduled()