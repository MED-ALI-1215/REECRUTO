import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import os

def send_email(recipient_email, subject, body, sender_email, sender_password):
    smtp_configs = [
        {"host": "smtp.gmail.com", "port": 465, "use_ssl": True,  "timeout": 30},
        {"host": "smtp.gmail.com", "port": 587, "use_tls": True,  "timeout": 30},
        {"host": "smtp.gmail.com", "port": 25,  "use_tls": True,  "timeout": 30},
    ]
    last_error = None
    for config in smtp_configs:
        try:
            msg = MIMEMultipart()
            msg['From']    = sender_email
            msg['To']      = recipient_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))
            if config.get("use_ssl"):
                server = smtplib.SMTP_SSL(config["host"], config["port"], timeout=config["timeout"])
            else:
                server = smtplib.SMTP(config["host"], config["port"], timeout=config["timeout"])
                if config.get("use_tls"):
                    server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
            server.quit()
            return True, "Email sent successfully!"
        except smtplib.SMTPAuthenticationError as e:
            return False, f"Authentication failed. Use Gmail App Password.\nError: {str(e)}"
        except Exception as e:
            last_error = str(e)
            continue
    return False, f"Failed after all SMTP attempts. Last error: {last_error}"


def generate_acceptance_email(candidate_name, job_title,
                               interview_link=None, interview_date=None):
    if interview_date is None:
        interview_date = (datetime.now() + timedelta(days=3)).strftime("%B %d, %Y")
    if interview_link is None:
        interview_link = "http://localhost:8502"

    subject = f"Congratulations! Next step for {job_title} — RECRUTO"
    body = f"""
    <html><head><meta charset="utf-8"></head>
    <body style="margin:0;padding:0;background:#0f1117;font-family:'Segoe UI',Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f1117;padding:40px 20px;">
        <tr><td align="center">
          <table width="600" cellpadding="0" cellspacing="0"
                 style="background:#161b27;border-radius:12px;overflow:hidden;border:1px solid #1e2a3a;">
            <tr><td style="background:linear-gradient(90deg,#fbbf24,#f59e0b);padding:4px 0;"></td></tr>
            <tr><td style="padding:32px 40px 0 40px;">
              <span style="font-size:22px;font-weight:900;letter-spacing:0.12em;color:#f1f5f9;text-transform:uppercase;">
                REC<span style="color:#fbbf24;">R</span>UTO
              </span>
            </td></tr>
            <tr><td style="padding:28px 40px 0 40px;">
              <h1 style="margin:0 0 6px;font-size:26px;font-weight:800;color:#f1f5f9;">
                Congratulations, {candidate_name}!
              </h1>
              <p style="margin:0 0 20px;font-size:15px;color:#64748b;line-height:1.6;">
                We reviewed your application for <strong style="color:#fbbf24;">{job_title}</strong>
                and we'd like to move you forward in the process.
              </p>
              <div style="background:#0d1520;border:1px solid #1e3a5f;border-left:4px solid #3b82f6;
                          border-radius:8px;padding:24px 28px;margin-bottom:28px;">
                <p style="margin:0 0 4px;font-size:12px;font-weight:700;letter-spacing:0.2em;
                           text-transform:uppercase;color:#3b82f6;">Next Step — AI Interview</p>
                <h2 style="margin:0 0 10px;font-size:18px;font-weight:800;color:#f1f5f9;">
                  Complete Your Online AI Interview
                </h2>
                <p style="margin:0 0 6px;font-size:14px;color:#475569;line-height:1.6;">
                  Takes 20-30 minutes. Deadline: <strong style="color:#94a3b8;">{interview_date}</strong>
                </p>
                <table cellpadding="0" cellspacing="0" style="margin-top:16px;">
                  <tr>
                    <td style="border-radius:8px;background:#3b82f6;">
                      <a href="{interview_link}"
                         style="display:inline-block;padding:14px 32px;font-size:14px;font-weight:800;
                                color:#ffffff;text-decoration:none;letter-spacing:0.08em;
                                text-transform:uppercase;border-radius:8px;">
                        Start My AI Interview
                      </a>
                    </td>
                  </tr>
                </table>
                <p style="margin:12px 0 0;font-size:11px;color:#1e3a5f;">
                  Link: <a href="{interview_link}" style="color:#3b82f6;">{interview_link}</a>
                  <br><em style="color:#334155;">This link is unique to you and can only be used once.</em>
                </p>
              </div>
              <p style="font-size:14px;color:#475569;line-height:1.7;">
                Questions? Reply to this email and we will be happy to help.
              </p>
            </td></tr>
            <tr><td style="padding:24px 40px 28px;border-top:1px solid #1e2a3a;">
              <p style="margin:0;font-size:14px;font-weight:700;color:#f1f5f9;">The RECRUTO Team</p>
            </td></tr>
            <tr><td style="background:linear-gradient(90deg,#fbbf24,#f59e0b);padding:3px 0;"></td></tr>
          </table>
        </td></tr>
      </table>
    </body></html>
    """
    return subject, body


def generate_rejection_email(candidate_name, job_title):
    subject = f"Your application for {job_title} — RECRUTO"
    body = f"""
    <html><head><meta charset="utf-8"></head>
    <body style="margin:0;padding:0;background:#0f1117;font-family:'Segoe UI',Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f1117;padding:40px 20px;">
        <tr><td align="center">
          <table width="600" cellpadding="0" cellspacing="0"
                 style="background:#161b27;border-radius:12px;overflow:hidden;border:1px solid #1e2a3a;">
            <tr><td style="background:#1e2a3a;padding:3px 0;"></td></tr>
            <tr><td style="padding:32px 40px 28px 40px;">
              <h1 style="margin:0 0 8px;font-size:22px;font-weight:800;color:#f1f5f9;">Dear {candidate_name},</h1>
              <p style="margin:0 0 18px;font-size:15px;color:#64748b;line-height:1.7;">
                Thank you for your interest in the
                <strong style="color:#94a3b8;">{job_title}</strong> position.
              </p>
              <div style="background:#0d1520;border-left:4px solid #475569;border-radius:8px;padding:18px 24px;margin-bottom:22px;">
                <p style="margin:0;font-size:14px;color:#475569;line-height:1.7;">
                  After careful consideration we have decided to move forward with other candidates.
                  We genuinely appreciate the time you invested in your application.
                </p>
              </div>
              <p style="font-size:14px;color:#475569;">We wish you every success in your career journey.</p>
              <p style="margin-top:24px;font-size:14px;font-weight:700;color:#f1f5f9;">The RECRUTO Team</p>
            </td></tr>
            <tr><td style="background:#1e2a3a;padding:3px 0;"></td></tr>
          </table>
        </td></tr>
      </table>
    </body></html>
    """
    return subject, body