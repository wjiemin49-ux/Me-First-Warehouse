"""邮件发送器"""
from __future__ import annotations

import logging
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ..models.news_item import DailyReport
from ..utils.time_utils import format_datetime_zh

logger = logging.getLogger(__name__)


class EmailSender:
    """邮件发送器"""

    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.qq.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.email_from = os.getenv('EMAIL_FROM')
        self.email_to = os.getenv('EMAIL_TO')

        if not all([self.smtp_username, self.smtp_password, self.email_from, self.email_to]):
            raise ValueError("邮件配置不完整，请检查环境变量")

    def send(self, report: DailyReport) -> bool:
        """发送邮件"""
        try:
            # 生成邮件内容
            subject = f"【AI热点日报】{report.date.strftime('%Y-%m-%d')}"
            html_body = self._generate_html(report)
            text_body = self._generate_text(report)

            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_from
            msg['To'] = self.email_to
            msg['Subject'] = subject

            # 添加纯文本和 HTML 版本
            msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))

            # 发送邮件
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            logger.info(f"邮件发送成功: {self.email_to}")
            return True

        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False

    def _generate_html(self, report: DailyReport) -> str:
        """生成 HTML 邮件内容"""
        items_html = []

        for item in report.items:
            priority_class = 'priority-high' if item.priority >= 4 else ''
            priority_label = '🔥 高优先级' if item.priority >= 4 else ''

            item_html = f"""
            <div class="news-item {priority_class}">
                <h3>{item.title_zh}</h3>
                <p class="meta">
                    <strong>来源:</strong> {item.source} |
                    <strong>发布时间:</strong> {format_datetime_zh(item.published_utc)}
                    {f' | <span style="color: #d32f2f;">{priority_label}</span>' if priority_label else ''}
                </p>
                <p>{item.summary_zh}</p>
                <p><a href="{item.url}" target="_blank">查看原文 →</a></p>
            </div>
            """
            items_html.append(item_html)

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #1a73e8 0%, #4285f4 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .summary {{
            background: #f8f9fa;
            padding: 20px;
            margin: 0;
            border-bottom: 1px solid #e0e0e0;
        }}
        .summary h2 {{
            margin: 0 0 15px 0;
            font-size: 18px;
            color: #333;
        }}
        .summary ul {{
            margin: 0;
            padding-left: 20px;
        }}
        .summary li {{
            margin: 5px 0;
            color: #666;
        }}
        .content {{
            padding: 20px;
        }}
        .content h2 {{
            font-size: 20px;
            color: #333;
            margin: 0 0 20px 0;
        }}
        .news-item {{
            border-left: 4px solid #1a73e8;
            padding: 20px;
            margin: 0 0 20px 0;
            background: #fafafa;
            border-radius: 4px;
        }}
        .news-item.priority-high {{
            border-left-color: #d32f2f;
            background: #fff3f3;
        }}
        .news-item h3 {{
            margin: 0 0 10px 0;
            font-size: 18px;
            color: #333;
        }}
        .news-item p {{
            margin: 10px 0;
            line-height: 1.6;
            color: #555;
        }}
        .news-item .meta {{
            font-size: 14px;
            color: #666;
            margin: 5px 0;
        }}
        .news-item a {{
            color: #1a73e8;
            text-decoration: none;
        }}
        .news-item a:hover {{
            text-decoration: underline;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 14px;
            border-top: 1px solid #e0e0e0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 AI热点日报</h1>
            <p>{report.date.strftime('%Y年%m月%d日')}</p>
        </div>

        <div class="summary">
            <h2>📊 今日摘要</h2>
            <ul>
                <li>共抓取 <strong>{report.total_fetched}</strong> 条新闻</li>
                <li>去重后保留 <strong>{report.total_after_dedup}</strong> 条</li>
                <li>推送 <strong>{report.total_sent}</strong> 条高价值内容</li>
            </ul>
        </div>

        <div class="content">
            <h2>🔥 重点新闻</h2>
            {''.join(items_html) if items_html else '<p>今日暂无新闻</p>'}
        </div>

        <div class="footer">
            <p>生成时间: {format_datetime_zh(datetime.now())}</p>
            <p>本邮件由 AI 每日新闻自动化脚本生成</p>
        </div>
    </div>
</body>
</html>
        """
        return html

    def _generate_text(self, report: DailyReport) -> str:
        """生成纯文本邮件内容"""
        lines = [
            f"AI热点日报 - {report.date.strftime('%Y年%m月%d日')}",
            "=" * 50,
            "",
            "今日摘要:",
            f"- 共抓取 {report.total_fetched} 条新闻",
            f"- 去重后保留 {report.total_after_dedup} 条",
            f"- 推送 {report.total_sent} 条高价值内容",
            "",
            "重点新闻:",
            "=" * 50,
            "",
        ]

        for idx, item in enumerate(report.items, 1):
            priority_mark = "🔥 " if item.priority >= 4 else ""
            lines.extend([
                f"{idx}. {priority_mark}{item.title_zh}",
                f"   来源: {item.source}",
                f"   时间: {format_datetime_zh(item.published_utc)}",
                f"   摘要: {item.summary_zh}",
                f"   链接: {item.url}",
                "",
            ])

        lines.extend([
            "=" * 50,
            f"生成时间: {format_datetime_zh(datetime.now())}",
        ])

        return '\n'.join(lines)
