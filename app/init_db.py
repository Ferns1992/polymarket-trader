from app.database import SessionLocal, engine, Base
from app.models.models import User, AISettings, BotSettings
from app.api.routes import get_password_hash
import json


def init_db():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.username == "fabian").first()
        if not existing_user:
            user = User(
                username="fabian",
                password_hash=get_password_hash("polymarket123"),
            )
            db.add(user)
            print("Created user: fabian")

        ai_settings = db.query(AISettings).first()
        if not ai_settings:
            ai_settings = AISettings(
                provider="ollama",
                model="llama2",
                ollama_url="http://localhost:11434",
                lmstudio_url="http://localhost:1234/v1",
                prompt_template="You are a trading assistant. Analyze this market and decide: Should I buy YES or NO? Just answer with YES, NO, or HOLD.",
                enabled=False,
            )
            db.add(ai_settings)
            print("Created AI settings")

        bot_settings_keys = [
            "bot_running",
            "auto_trade",
            "stake_amount",
            "selected_markets",
        ]
        for key in bot_settings_keys:
            existing = db.query(BotSettings).filter(BotSettings.key == key).first()
            if not existing:
                default_value = (
                    "false"
                    if key in ["bot_running", "auto_trade"]
                    else ("10" if key == "stake_amount" else "[]")
                )
                setting = BotSettings(key=key, value=default_value)
                db.add(setting)

        db.commit()
        print("Database initialized successfully!")

    except Exception as e:
        print(f"Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
