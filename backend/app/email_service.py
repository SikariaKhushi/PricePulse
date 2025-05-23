# email_service.py
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import asyncio
import aiosmtplib

# Email configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USERNAME)

async def send_price_drop_alert(
    to_email: str,
    user_name: str,
    product_name: str,
    product_image: str,
    current_price: float,
    target_price: float,
    product_url: str
):
    """Send price drop alert email"""
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print("Email configuration not set. Skipping email notification.")
        return
    
    subject = f"🎉 Price Drop Alert: {product_name}"
    
    # HTML email template
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
            .content {{ padding: 30px; }}
            .product-info {{ display: flex; align-items: center; margin: 20px 0; padding: 20px; background-color: #f8f9fa; border-radius: 8px; }}
            .product-image {{ width: 100px; height: 100px; object-fit: cover; border-radius: 8px; margin-right: 20px; }}
            .price-info {{ margin: 20px 0; }}
            .current-price {{ font-size: 24px; color: #28a745; font-weight: bold; }}
            .target-price {{ font-size: 16px; color: #6c757d; text-decoration: line-through; }}
            .savings {{ font-size: 18px; color: #dc3545; font-weight: bold; }}
            .cta-button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 20px 0; }}
            .footer {{ padding: 20px; background-color: #f8f9fa; text-align: center; color: #6c757d; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎉 Price Drop Alert!</h1>
                <p>Hi {user_name}, great news! The price has dropped on a product you're tracking.</p>
            </div>
            
            <div class="content">
                <div class="product-info">
                    <img src="{product_image}" alt="{product_name}" class="product-image" onerror="this.style.display='none'">
                    <div>
                        <h3>{product_name}</h3>
                        <p>The product you've been waiting for is now available at your target price!</p>
                    </div>
                </div>
                
                <div class="price-info">
                    <div class="current-price">₹{current_price:,.2f}</div>
                    <div class="target-price">Target Price: ₹{target_price:,.2f}</div>
                    <div class="savings">You save: ₹{target_price - current_price:,.2f}</div>
                </div>
                
                <a href="{product_url}" class="cta-button">Buy Now</a>
                
                <p><small>⚡ Hurry! Prices can change quickly. Don't miss out on this deal!</small></p>
            </div>
            
            <div class="footer">
                <p>This alert was sent because you set a price alert for this product.</p>
                <p>© 2024 PricePulse - Your Smart Shopping Companion</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Plain text version
    text_body = f"""
    🎉 Price Drop Alert!
    
    Hi {user_name},
    
    Great news! The price has dropped on "{product_name}"!
    
    Current Price: ₹{current_price:,.2f}
    Your Target: ₹{target_price:,.2f}
    You Save: ₹{target_price - current_price:,.2f}
    
    Buy now: {product_url}
    
    Hurry! Prices can change quickly.
    
    © 2024 PricePulse
    """
    
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = FROM_EMAIL
        message["To"] = to_email
        
        # Add text and HTML parts
        text_part = MIMEText(text_body, "plain")
        html_part = MIMEText(html_body, "html")
        
        message.attach(text_part)
        message.attach(html_part)
        
        # Send email asynchronously
        await aiosmtplib.send(
            message,
            hostname=SMTP_SERVER,
            port=SMTP_PORT,
            start_tls=True,
            username=SMTP_USERNAME,
            password=SMTP_PASSWORD,
        )
        
        print(f"Price drop alert sent to {to_email}")
        
    except Exception as e:
        print(f"Failed to send email to {to_email}: {str(e)}")

async def send_welcome_email(to_email: str, user_name: str):
    """Send welcome email to new users"""
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        return
    
    subject = "Welcome to PricePulse! 🎉"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
            .content {{ padding: 30px; }}
            .feature {{ margin: 20px 0; padding: 15px; background-color: #f8f9fa; border-radius: 8px; }}
            .footer {{ padding: 20px; background-color: #f8f9fa; text-align: center; color: #6c757d; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to PricePulse! 🎉</h1>
                <p>Hi {user_name}, thanks for joining our smart shopping community!</p>
            </div>
            
            <div class="content">
                <p>You're now part of a community that never misses a great deal. Here's what you can do with PricePulse:</p>
                
                <div class="feature">
                    <h3>📊 Track Prices</h3>
                    <p>Monitor prices of your favorite products across multiple platforms.</p>
                </div>
                
                <div class="feature">
                    <h3>🔔 Get Alerts</h3>
                    <p>Receive instant notifications when prices drop to your target.</p>
                </div>
                
                <div class="feature">
                    <h3>🔍 Compare Prices</h3>
                    <p>Find the best deals across Amazon, Flipkart, and Meesho.</p>
                </div>
                
                <p>Start by adding your first product to track and set price alerts!</p>
            </div>
            
            <div class="footer">
                <p>Happy shopping!</p>
                <p>© 2024 PricePulse Team</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = FROM_EMAIL
        message["To"] = to_email
        
        html_part = MIMEText(html_body, "html")
        message.attach(html_part)
        
        await aiosmtplib.send(
            message,
            hostname=SMTP_SERVER,
            port=SMTP_PORT,
            start_tls=True,
            username=SMTP_USERNAME,
            password=SMTP_PASSWORD,
        )
        
        print(f"Welcome email sent to {to_email}")
        
    except Exception as e:
        print(f"Failed to send welcome email to {to_email}: {str(e)}")

# Synchronous version for testing
def send_test_email(to_email: str):
    """Send test email (synchronous version)"""
    try:
        msg = MIMEText("This is a test email from PricePulse API!")
        msg['Subject'] = "PricePulse Test Email"
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"Test email sent to {to_email}")
        return True
        
    except Exception as e:
        print(f"Failed to send test email: {str(e)}")
        return False