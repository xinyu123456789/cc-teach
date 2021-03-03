from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class SI(models.Model):
    name = models.CharField('廠商名稱', max_length=64)
    phone = models.CharField('聯絡電話', max_length=32)
    memo = models.TextField('備註', blank=True, null=True)

    def __str__(self):
        return self.name

def model_pic_name(instance, filename):
    fn = "model/{}.jpg".format(instance.name.replace(' ', '_'))
    return fn

class Model(models.Model):
    STATUS_CHOICES = [
        (0, '列帳'),
        (1, '報廢除帳'),
    ]

    CATEGORY_CHOICES = [
        (0, 'NB'),
        (1, 'PC'),
        (2, '攝影設備'),
        (3, '網路設備'),
        (4, '影音週邊'),
        (5, '其他週邊'),
    ]

    name = models.CharField('型號', max_length=64)
    date_buy = models.DateField('購置日期')
    specification = models.TextField('詳細規格', blank=True, null=True)
    status = models.IntegerField('狀態', choices=STATUS_CHOICES, default=0)
    category = models.IntegerField('設備類別', choices=CATEGORY_CHOICES)
    si = models.ForeignKey(SI, models.SET_NULL, blank=True, null=True)
    oid = models.IntegerField('舊編號', default=0)
    modified = models.DateTimeField('更新時間', auto_now=True)
    pic = models.ImageField('圖片', upload_to=model_pic_name, blank=True, null=True)

    def __str__(self):
        return "{} - {}".format(
            self.get_category_display(),
            self.name,
        )

class Equip(models.Model):
    STATUS_CHOICE = [
        (0, '正常'), 
        (1, '故障:待修'), 
        (2, '故障:原廠送修'),
        (8, '故障:待報廢'),
        (9, '已報廢'),
    ]
    STATUS_CLASS = {
        0: 'uk-label uk-label-success', 
        1: 'uk-label uk-label-warning',
        2: 'uk-label uk-label-warning',
        8: 'uk-label uk-label-warning',
        9: 'uk-label uk-label-danger',
    }
    model = models.ForeignKey(Model, models.CASCADE)
    name = models.CharField('設備編號', max_length=32)
    prop_no = models.CharField('財產編號', max_length=32, blank=True, null=True)
    barcode = models.CharField('條碼序號', max_length=16, blank=True, null=True)
    memo = models.TextField('備註', blank=True, null=True)
    status = models.IntegerField('狀態', choices=STATUS_CHOICE, default=0)
    oid = models.IntegerField('舊編號', default=0)
    modified = models.DateTimeField('更新時間', auto_now=True)

    def __str__(self):
        return self.name

    def render_status_label(self):
        return f"<span class='{self.STATUS_CLASS[self.status]}'>{self.get_status_display()}</span>"
        

class Applicant(models.Model):
    STATUS_CHOICES = [
        (0, '在職'),
        (1, '已離職'),
        (2, '留職停薪'),
    ]

    ROLE_CHOICES = [
        (0, '行政人員'), 
        (1, '高中部教師'), 
        (2, '國中部教師'),
    ]

    role = models.IntegerField('身分', choices=ROLE_CHOICES)
    status = models.IntegerField('狀態', choices=STATUS_CHOICES, default=0)
    name = models.CharField('姓名', max_length=32)
    email = models.EmailField('電子郵件', max_length=128)
    phone = models.CharField('聯絡電話', max_length=32)
    oid = models.IntegerField('舊編號', default=0)
    modified = models.DateTimeField('更新時間', auto_now=True)

    def __str__(self):
        return "{}:{}".format(
            self.get_role_display(), 
            self.name,
        )

class Log(models.Model):
    equip = models.ForeignKey(Equip, models.CASCADE, verbose_name='設備')
    user = models.ForeignKey(Applicant, models.CASCADE, verbose_name='借用人')
    date_apply = models.DateField('借出日期')
    date_return = models.DateField('歸還日期', blank=True, null=True)
    oid = models.IntegerField('舊編號', default=0)
    modified = models.DateTimeField('更新時間', auto_now=True)
    author = models.ForeignKey(User, models.CASCADE, verbose_name='登錄人', default=1)

    def __str__(self):
        return "{}:{}:{}".format(
            self.date_apply.strftime("Y-m-d"),
            self.user.name, 
            self.equip.name,
        )

class Inventory(models.Model):
    year = models.IntegerField('盤點年度')
    invlist = models.JSONField()

    def __str__(self):
        return str(self.year)+"年度"

class InventoryLog(models.Model):
    equip = models.ForeignKey(Equip, models.CASCADE, verbose_name='設備')
    date_checked = models.DateTimeField('盤點日期', auto_now=True)
    author = models.ForeignKey(User, models.CASCADE, verbose_name='登錄人', default=1)

    def __str__(self):
        return "{} {} {}".format(
            self.date_checked,
            self.equip.name, 
            self.author.first_name,
        )