from sqlalchemy import Column, Integer, String, Uuid, ForeignKey, BigInteger
from sqlalchemy.orm import relationship, declarative_base


Base = declarative_base()


class UserModel(Base):
    __tablename__ = 'users'
    user_id = Column(Uuid, primary_key=True)
    name = Column(String(255), nullable=False)
    surname = Column(String(255), nullable=False)
    photo_url = Column(String(255))
    phone_number = Column(String(20))
    email = Column(String(255), unique=True, nullable=False)
    hashed_password_base64 = Column(String(255), nullable=False)
    cart_entries = relationship('ShoppingCartEntry', back_populates='user_model')

    def to_dict(self):
        return {
            'user_id': str(self.user_id),
            'name': self.name,
            'surname': self.surname,
            'photo_url': self.photo_url,
            'phone_number': self.phone_number,
            'email': self.email,
        }


class ShoppingCartEntry(Base):
    __tablename__ = 'shopping_cart_entries'
    entry_id = Column(BigInteger, primary_key=True)
    product_id = Column(Uuid, nullable=False)
    user_id = Column(Uuid, ForeignKey('users.user_id'), nullable=False)
    quantity = Column(Integer, default=1)

    user_model = relationship('UserModel', back_populates='cart_entries')

    def to_dict(self):
        return {
            'entry_id': int(self.entry_id),
            'product_id': self.product_id,
            'user_id': self.user_id,
            'quantity': self.quantity,
        }
