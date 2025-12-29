from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

favoriler_tablo = db.Table('favoriler',
                           db.Column('kullanici_id', db.Integer, db.ForeignKey('kullanici.id'), primary_key=True),
                           db.Column('kitap_id', db.Integer, db.ForeignKey('kitap.id'), primary_key=True)
                           )


class Kullanici(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    sifre = db.Column(db.String(100), nullable=False)
    isim = db.Column(db.String(100))
    rol = db.Column(db.String(20), default='uye')
    yorumlar = db.relationship('Yorum', backref='yazar', lazy=True)
    islemler = db.relationship('OduncIslemi', backref='kullanici', lazy=True)
    favoriler = db.relationship('Kitap', secondary=favoriler_tablo, backref=db.backref('sevenler', lazy='dynamic'))


class Kitap(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(100))
    yazar = db.Column(db.String(100))
    ozet = db.Column(db.Text)
    fotograf_url = db.Column(db.String(255))
    adet = db.Column(db.Integer, default=1)
    ceza_tutari = db.Column(db.Float, default=50.0)
    yorumlar = db.relationship('Yorum', backref='kitap', lazy=True, cascade="all, delete-orphan")


class OduncIslemi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kitap_id = db.Column(db.Integer, db.ForeignKey('kitap.id'))
    kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanici.id'))
    alis_tarihi = db.Column(db.DateTime, default=datetime.now)
    teslim_edildi = db.Column(db.Boolean, default=False)
    borc_odendi = db.Column(db.Boolean, default=False)
    kitap = db.relationship('Kitap', backref='odunc_islemleri')

    def ceza_hesapla(self):
        if self.borc_odendi:
            return 0.0
        gecen_sure = datetime.now() - self.alis_tarihi
        # 60 saniyeden sonra ceza tutarını döndürür
        if gecen_sure.total_seconds() > 60:
            return self.kitap.ceza_tutari
        return 0.0


class Yorum(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kitap_id = db.Column(db.Integer, db.ForeignKey('kitap.id'))
    kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanici.id'))
    yorum_metni = db.Column(db.Text, nullable=False)
    yorum_tarihi = db.Column(db.DateTime, default=datetime.utcnow)