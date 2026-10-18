from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from sqlalchemy.orm import Session
from sqlalchemy import func
from database import engine, SessionLocal, Base
from models import TransactionDB

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from auth import verify_password, create_access_token, fake_users_db, SECRET_KEY, ALGORITHM
from jose import JWTError, jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.mount("/dashboard", StaticFiles(directory="static", html=True), name="dashboard")

class Transaction(BaseModel):
    account_id: int = Field(..., gt=0, description="Must be a positive account ID")
    amount: float = Field(..., gt=0, description="Transaction amount must be positive")
    merchant: str = Field(..., min_length=1, max_length=100)
    category: str = ""

    @field_validator("merchant")
    @classmethod
    def merchant_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("merchant cannot be blank or whitespace only")
        return v.strip()

#add merchants here
MERCHANT_CATEGORIES = {
    "starbucks": "coffee",
    "luckin coffee": "coffee",
    "village grocer": "groceries",
    "jaya grocer": "groceries",
}


def normalize(text: str) -> str:
    return text.strip().lower().replace("_", " ").replace("-", " ")


def categorize(merchant: str, user_supplied_category: str = "") -> str:
    known_category = MERCHANT_CATEGORIES.get(normalize(merchant))
    if known_category:
        return known_category
    if user_supplied_category.strip():
        return normalize(user_supplied_category)
    return "uncategorized"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = fake_users_db.get(username)
    if user is None:
        raise credentials_exception
    return user


@app.get("/")
def read_root():
    return {"status": "Transaction API is running!"}


@app.post("/transactions")
def add_transaction(
    new_transaction: Transaction,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    category = categorize(new_transaction.merchant, new_transaction.category)

    db_transaction = TransactionDB(
        account_id=new_transaction.account_id,
        amount=new_transaction.amount,
        merchant=new_transaction.merchant,
        category=category,
        owner=current_user["username"],
    )

    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    return {
        "message": "Successful transaction!",
        "transaction": db_transaction
    }


@app.get("/transactions")
def get_transactions(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return (
        db.query(TransactionDB)
        .filter(TransactionDB.owner == current_user["username"])
        .all()
    )


@app.get("/transactions/summary")
def get_summary(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_transactions = db.query(TransactionDB).filter(
        TransactionDB.owner == current_user["username"]
    )

    total_spent = user_transactions.with_entities(func.sum(TransactionDB.amount)).scalar() or 0
    transaction_count = user_transactions.count()

    by_category = (
        user_transactions.with_entities(
            TransactionDB.category, func.sum(TransactionDB.amount)
        )
        .group_by(TransactionDB.category)
        .all()
    )

    return {
        "total_spent": round(total_spent, 2),
        "transaction_count": transaction_count,
        "by_category": {category: round(amount, 2) for category, amount in by_category},
    }


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = fake_users_db.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}