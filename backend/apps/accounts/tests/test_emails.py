import pytest
from apps.accounts.emails import _render_plain_text, send_email


def test_plain_text_removes_styles_tags_and_preserves_readability():
    text = _render_plain_text("<style>.x { color:red; }</style><p>Hello</p><div>MD<br/>Welcome</div>")
    assert text == "Hello\nMD\nWelcome"
    assert "color" not in text


def test_verification_template_sends_html_and_plain_text(mailoutbox, settings):
    link = "https://shop.example.test/verify-email?token=test-token"
    send_email(subject="Verify your email", template_name="emails/verify_email.html",
               context={"user_name": "MD", "verify_url": link}, recipient="md@example.com")
    assert len(mailoutbox) == 1
    message = mailoutbox[0]
    assert message.subject == "Verify your email"
    assert message.to == ["md@example.com"]
    assert message.from_email == settings.DEFAULT_FROM_EMAIL
    assert link in message.body
    assert "<style" not in message.body
    assert message.alternatives[0].mimetype == "text/html"
    assert link in message.alternatives[0].content
    assert settings.BRAND_NAME in message.alternatives[0].content


def test_caller_context_can_override_base_context(mailoutbox):
    send_email(subject="Verify", template_name="emails/verify_email.html",
               context={"brand_name": "TestBrand", "user_name": "MD", "verify_url": "https://example.test"},
               recipient="md@example.com")
    assert "TestBrand" in mailoutbox[0].alternatives[0].content


def test_delivery_failure_propagates_for_task_retry(mocker):
    mocker.patch("apps.accounts.emails.EmailMultiAlternatives.send", side_effect=RuntimeError("mail down"))
    with pytest.raises(RuntimeError, match="mail down"):
        send_email(subject="Verify", template_name="emails/verify_email.html",
                   context={"user_name": "MD", "verify_url": "https://example.test"}, recipient="md@example.com")
