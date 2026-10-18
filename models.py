from sqlalchemy import Column, Integer, Float, String
from database import Base


class TransactionDB(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, index=True)
    amount = Column(Float)
    merchant = Column(String)
    category = Column(String, default="")
    owner = Column(String, index=True)