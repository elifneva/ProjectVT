import string
import random
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mail import Mail, Message
from models import db, Kitap, OduncIslemi, Kullanici, Yorum
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kutuphane.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'elif01_secure_system_v8'

# --- MAIL AYARLARI ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = '321elifozturk@gmail.com'
app.config['MAIL_PASSWORD'] = 'idws hnvt qjzn fjlm'
app.config['MAIL_DEFAULT_SENDER'] = '321elifozturk@gmail.com'

mail = Mail(app)
db.init_app(app)


def rastgele_sifre(length=8):
    return ''.join(random.choice(string.ascii_letters + string.digits) for i in range(length))


with app.app_context():
    db.create_all()
    if not Kullanici.query.filter_by(email='elif01@gmail.com').first():
        admin = Kullanici(email='elif01@gmail.com', sifre='0101', isim='Elif', rol='admin')
        db.session.add(admin)
        db.session.commit()


@app.route('/')
def ana_sayfa():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = Kullanici.query.get(session['user_id'])

    # ödenmemiş borçları gösteriyor.
    toplam_borc = sum(i.ceza_hesapla() for i in user.islemler if not i.borc_odendi)

    return render_template('index.html',
                           kitaplar=Kitap.query.all(),
                           uyeler=Kullanici.query.filter(Kullanici.rol != 'admin').all(),
                           user=user,
                           toplam_borc=toplam_borc)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = Kullanici.query.filter_by(email=request.form.get('email'), sifre=request.form.get('sifre')).first()
        if user:
            session.update({'user_id': user.id, 'user_rol': user.rol, 'user_isim': user.isim})
            return redirect(url_for('ana_sayfa'))
        flash("E-posta veya şifre hatalı!", "danger")
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        if Kullanici.query.filter_by(email=email).first():
            flash("Bu e-posta zaten kayıtlı!", "danger")
        else:
            sifre = rastgele_sifre()
            yeni = Kullanici(email=email, isim=request.form.get('isim'), sifre=sifre)
            db.session.add(yeni)
            db.session.commit()
            try:
                msg = Message('Kütüphane Giriş Şifreniz', recipients=[email])
                msg.body = f"Merhaba {yeni.isim},\n\nSisteme giriş şifreniz: {sifre}"
                mail.send(msg)
                flash("Kayıt başarılı! Şifreniz mail adresinize gönderildi.", "success")
            except:
                flash("Kayıt yapıldı ancak mail gönderilemedi. Admin ile görüşün.", "warning")
            return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/odunc_al/<int:kitap_id>')
def odunc_al(kitap_id):
    user_id = session['user_id']
    kitap = Kitap.query.get(kitap_id)
    mevcut_islem = OduncIslemi.query.filter_by(kullanici_id=user_id, kitap_id=kitap_id, teslim_edildi=False).first()

    if mevcut_islem:
        flash(f"'{kitap.baslik}' kitabı zaten sizde bulunuyor. Önce iade etmelisiniz!", "warning")
    elif kitap.adet <= 0:
        flash("Bu kitap şu an stokta kalmadı!", "danger")
    else:
        yeni_islem = OduncIslemi(kitap_id=kitap_id, kullanici_id=user_id)
        kitap.adet -= 1
        db.session.add(yeni_islem)
        db.session.commit()
        flash(f"'{kitap.baslik}' ödünç alındı. Keyifli okumalar!", "success")
    return redirect(url_for('ana_sayfa'))


@app.route('/teslim_et/<int:id>')
def teslim_et(id):
    islem = OduncIslemi.query.get(id)
    if islem and not islem.teslim_edildi:
        islem.teslim_edildi = True
        islem.kitap.adet += 1
        db.session.commit()
        flash(f"'{islem.kitap.baslik}' başarıyla iade edildi.", "success")
    return redirect(url_for('ana_sayfa'))


@app.route('/odeme_yap', methods=['POST'])
def odeme_yap():
    user = Kullanici.query.get(session['user_id'])
    odenen_adet = 0
    for i in user.islemler:
        if not i.borc_odendi and i.ceza_hesapla() > 0:
            i.borc_odendi = True
            odenen_adet += 1
    db.session.commit()
    if odenen_adet > 0:
        flash("Ödeme başarılı! Tüm borçlarınız sıfırlandı.", "success")
    else:
        flash("Ödenecek borcunuz bulunmuyor.", "info")
    return redirect(url_for('ana_sayfa'))


@app.route('/ekle', methods=['POST'])
def ekle():
    if session.get('user_rol') == 'admin':
        k = Kitap(
            baslik=request.form.get('baslik'),
            yazar=request.form.get('yazar'),
            ozet=request.form.get('ozet'),
            fotograf_url=request.form.get('fotograf_url'),
            adet=int(request.form.get('adet', 1)),
            ceza_tutari=float(request.form.get('ceza_tutari', 50))
        )
        db.session.add(k)
        db.session.commit()
        flash("Yeni kitap eklendi.", "success")
    return redirect(url_for('ana_sayfa'))


@app.route('/favori/<int:id>')
def favori(id):
    u = Kullanici.query.get(session['user_id'])
    k = Kitap.query.get(id)
    if k in u.favoriler:
        u.favoriler.remove(k)
        flash("Favorilerden çıkarıldı.", "info")
    else:
        u.favoriler.append(k)
        flash("Favorilere eklendi!", "success")
    db.session.commit()
    return redirect(url_for('ana_sayfa'))


@app.route('/yorum_yap/<int:kitap_id>', methods=['POST'])
def yorum_yap(kitap_id):
    metin = request.form.get('yorum_metni')
    if metin:
        y = Yorum(kitap_id=kitap_id, kullanici_id=session['user_id'], yorum_metni=metin)
        db.session.add(y)
        db.session.commit()
        flash("Yorumunuz eklendi.", "success")
    return redirect(url_for('ana_sayfa'))


@app.route('/uye_sil/<int:id>')
def uye_sil(id):
    if session.get('user_rol') == 'admin':
        u = Kullanici.query.get(id)
        db.session.delete(u)
        db.session.commit()
        flash("Üye silindi.", "danger")
    return redirect(url_for('ana_sayfa'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True)