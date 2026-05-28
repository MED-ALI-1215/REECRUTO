import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import get_settings
from app.core.exceptions import EmailDeliveryError
from app.core.logging import get_logger

logger = get_logger(__name__)


def send_email(recipient_email: str, subject: str, html_body: str) -> None:
    settings = get_settings()
    configs = [
        {"host": "smtp.gmail.com", "port": 465, "ssl": True},
        {"host": "smtp.gmail.com", "port": 587, "tls": True},
    ]
    last_error = ""
    for cfg in configs:
        try:
            msg = MIMEMultipart()
            msg["From"] = settings.EMAIL_ADDRESS
            msg["To"] = recipient_email
            msg["Subject"] = subject
            msg.attach(MIMEText(html_body, "html"))
            if cfg.get("ssl"):
                server = smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=30)
            else:
                server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=30)
                if cfg.get("tls"):
                    server.starttls()
            server.login(settings.EMAIL_ADDRESS, settings.EMAIL_PASSWORD)
            server.sendmail(settings.EMAIL_ADDRESS, recipient_email, msg.as_string())
            server.quit()
            logger.info("Email sent to=%s subject=%r", recipient_email, subject)
            return
        except smtplib.SMTPAuthenticationError as e:
            raise EmailDeliveryError("SMTP authentication failed — check EMAIL_ADDRESS and EMAIL_PASSWORD") from e
        except Exception as e:
            last_error = str(e)
            continue
    raise EmailDeliveryError(f"All SMTP attempts failed. Last error: {last_error}")


def generate_invite_email(candidate_name: str, job_title: str, interview_link: str) -> tuple[str, str]:
    deadline = (datetime.now() + timedelta(days=3)).strftime("%B %d, %Y")
    subject = f"Interview Invitation — {job_title} | REECRUTO"
    body = f"""
    <html><head><meta charset="utf-8"></head>
    <body style="margin:0;padding:0;background:#0f1117;font-family:'Segoe UI',Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f1117;padding:40px 20px;">
        <tr><td align="center">
          <table width="600" cellpadding="0" cellspacing="0"
                 style="background:#161b27;border-radius:12px;overflow:hidden;border:1px solid #1e2a3a;">
            <tr><td style="background:linear-gradient(90deg,#fbbf24,#f59e0b);padding:4px 0;"></td></tr>
            <tr><td style="padding:32px 40px 32px 40px;">
              <span style="font-size:20px;font-weight:900;letter-spacing:0.12em;color:#f1f5f9;text-transform:uppercase;">
                REC<span style="color:#fbbf24;">R</span>UTO
              </span>
              <h1 style="margin:20px 0 6px;font-size:24px;font-weight:800;color:#f1f5f9;">
                Hello, {candidate_name}!
              </h1>
              <p style="margin:0 0 20px;font-size:15px;color:#64748b;line-height:1.6;">
                Congratulations — you have been selected to move forward for the
                <strong style="color:#fbbf24;">{job_title}</strong> position.
              </p>
              <div style="background:#0d1520;border-left:4px solid #3b82f6;border-radius:8px;padding:20px 24px;margin-bottom:24px;">
                <p style="margin:0 0 8px;font-size:12px;font-weight:700;text-transform:uppercase;color:#3b82f6;">
                  Next Step — Online AI Interview
                </p>
                <p style="margin:0 0 14px;font-size:14px;color:#475569;">
                  Complete your online AI interview before <strong style="color:#94a3b8;">{deadline}</strong>.
                </p>
                <a href="{interview_link}"
                   style="display:inline-block;padding:12px 28px;font-size:14px;font-weight:700;
                          color:#ffffff;text-decoration:none;background:#3b82f6;border-radius:8px;">
                  Start AI Interview
                </a>
                <p style="margin:10px 0 0;font-size:11px;color:#334155;">
                  <em>This link is unique to you and can only be used once.</em>
                </p>
              </div>
              <p style="margin:0;font-size:14px;color:#475569;">Best of luck,</p>
              <p style="margin:4px 0 0;font-size:14px;font-weight:700;color:#f1f5f9;">The REECRUTO Team</p>
            </td></tr>
            <tr><td style="background:linear-gradient(90deg,#fbbf24,#f59e0b);padding:3px 0;"></td></tr>
          </table>
        </td></tr>
      </table>
    </body></html>
    """
    return subject, body


def generate_acceptance_email(candidate_name: str, job_title: str) -> tuple[str, str]:
    """Sent after recruiter clicks Accept on the dashboard — informs candidate a f2f is coming."""
    subject = f"Great news about your {job_title} application — REECRUTO"
    body = f"""
    <html><head><meta charset="utf-8"></head>
    <body style="margin:0;padding:0;background:#0f1117;font-family:'Segoe UI',Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f1117;padding:40px 20px;">
        <tr><td align="center">
          <table width="600" cellpadding="0" cellspacing="0"
                 style="background:#161b27;border-radius:12px;overflow:hidden;border:1px solid #1e2a3a;">
            <tr><td style="background:linear-gradient(90deg,#22c55e,#16a34a);padding:4px 0;"></td></tr>
            <tr><td style="padding:32px 40px 32px 40px;">
              <span style="font-size:20px;font-weight:900;letter-spacing:0.12em;color:#f1f5f9;text-transform:uppercase;">
                REC<span style="color:#fbbf24;">R</span>UTO
              </span>
              <h1 style="margin:20px 0 6px;font-size:24px;font-weight:800;color:#f1f5f9;">
                Congratulations, {candidate_name}! 🎉
              </h1>
              <p style="margin:0 0 20px;font-size:15px;color:#64748b;line-height:1.6;">
                We are pleased to inform you that you have successfully passed the AI interview
                stage for the <strong style="color:#22c55e;">{job_title}</strong> position.
              </p>
              <div style="background:#0d2010;border-left:4px solid #22c55e;border-radius:8px;padding:20px 24px;margin-bottom:24px;">
                <p style="margin:0 0 8px;font-size:12px;font-weight:700;text-transform:uppercase;color:#22c55e;">
                  Next Step — Face-to-Face Interview
                </p>
                <p style="margin:0;font-size:14px;color:#475569;line-height:1.7;">
                  Our team will be in touch shortly to schedule your in-person interview.
                  Please keep an eye on your inbox for further details including the date,
                  time, and location.
                </p>
              </div>
              <p style="margin:0 0 4px;font-size:14px;color:#475569;">
                Thank you for your time and effort throughout this process.
                We look forward to meeting you in person.
              </p>
              <p style="margin:20px 0 0;font-size:14px;font-weight:700;color:#f1f5f9;">The REECRUTO Team</p>
            </td></tr>
            <tr><td style="background:linear-gradient(90deg,#22c55e,#16a34a);padding:3px 0;"></td></tr>
          </table>
        </td></tr>
      </table>
    </body></html>
    """
    return subject, body


def generate_rejection_email(candidate_name: str, job_title: str) -> tuple[str, str]:
    subject = f"Your application for {job_title} — REECRUTO"
    body = f"""
    <html><head><meta charset="utf-8"></head>
    <body style="margin:0;padding:0;background:#0f1117;font-family:'Segoe UI',Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f1117;padding:40px 20px;">
        <tr><td align="center">
          <table width="600" cellpadding="0" cellspacing="0"
                 style="background:#161b27;border-radius:12px;overflow:hidden;border:1px solid #1e2a3a;">
            <tr><td style="padding:32px 40px 28px 40px;">
              <span style="font-size:20px;font-weight:900;letter-spacing:0.12em;color:#f1f5f9;text-transform:uppercase;">
                REC<span style="color:#fbbf24;">R</span>UTO
              </span>
              <h1 style="margin:20px 0 8px;font-size:22px;font-weight:800;color:#f1f5f9;">Dear {candidate_name},</h1>
              <p style="margin:0 0 18px;font-size:15px;color:#64748b;line-height:1.7;">
                Thank you for your interest in the
                <strong style="color:#94a3b8;">{job_title}</strong> position
                and for the time you invested in the interview process.
              </p>
              <div style="background:#0d1520;border-left:4px solid #475569;border-radius:8px;padding:18px 24px;margin-bottom:22px;">
                <p style="margin:0;font-size:14px;color:#475569;line-height:1.7;">
                  After careful consideration, we have decided to move forward with other candidates
                  whose profiles more closely match our current requirements.
                  We genuinely appreciate your effort and wish you every success in your career.
                </p>
              </div>
              <p style="margin-top:20px;font-size:14px;font-weight:700;color:#f1f5f9;">The REECRUTO Team</p>
            </td></tr>
          </table>
        </td></tr>
      </table>
    </body></html>
    """
    return subject, body
