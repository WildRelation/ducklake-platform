from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Kund(Base):
    __tablename__ = "kunder"

    id = Column(Integer, primary_key=True, index=True)
    namn = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    telefon = Column(String)

    ordrar = relationship("Order", back_populates="kund")


class Produkt(Base):
    __tablename__ = "produkter"

    id = Column(Integer, primary_key=True, index=True)
    namn = Column(String, nullable=False)
    pris = Column(Float, nullable=False)
    lagersaldo = Column(Integer, default=0)

    ordrar = relationship("Order", back_populates="produkt")


class Order(Base):
    __tablename__ = "ordrar"

    id = Column(Integer, primary_key=True, index=True)
    kund_id = Column(Integer, ForeignKey("kunder.id"))
    produkt_id = Column(Integer, ForeignKey("produkter.id"))
    antal = Column(Integer, nullable=False)
    skapad = Column(DateTime, default=datetime.utcnow)

    kund = relationship("Kund", back_populates="ordrar")
    produkt = relationship("Produkt", back_populates="ordrar")
