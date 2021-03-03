from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, RedirectView, TemplateView, FormView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Subquery, OuterRef, Prefetch, Count
from django.urls import reverse_lazy
from datetime import date
from .models import *
from django import forms
from django.contrib import messages
from datetime import date
from django.http import HttpResponseRedirect
import pyexcel

# Create your views here.
class ModelList(PermissionRequiredMixin, ListView):
    permission_required = 'em.view_model'
    model = Model
    extra_context = {'model_category': Model.CATEGORY_CHOICES}

    def get_queryset(self):
        return super().get_queryset().annotate(equip_count=Count('equip'))

class ModelView(PermissionRequiredMixin, DetailView):
    permission_required = 'em.view_model'
    model = Model
    pk_url_kwarg = 'mid'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        sq = Log.objects.filter(
                equip = OuterRef('id'),
                date_return = None,
            )
        ctx['equip_list'] = self.object.equip_set.annotate(
            lend = Subquery(sq.values('date_apply')[:1]),
            uid = Subquery(sq.values('user_id')[:1]),
            user = Subquery(sq.values('user__name')[:1]),
        ).order_by('name')
        ctx['lend_list'] = ctx['equip_list'].exclude(lend=None)
        ctx['inhouse_list'] = ctx['equip_list'].filter(lend=None)
        return ctx

class EquipView(PermissionRequiredMixin, DetailView):
    permission_required = 'em.view_equip'
    model = Equip
    pk_url_kwarg = 'eid'

    def get_queryset(self):
        return super().get_queryset().prefetch_related(
            Prefetch(
                'log_set', 
                queryset = Log.objects.select_related('user').order_by('-date_apply'),
            ),
        ).annotate(
            lend = Subquery(Log.objects.filter(equip = OuterRef('id'), date_return = None).values('date_apply')[:1])
        )

class ApplicantList(PermissionRequiredMixin, ListView):
    permission_required = 'em.view_applicant'
    model = Applicant
    ordering = ['name']

class ApplicantView(PermissionRequiredMixin, DetailView):
    permission_required = 'em.view_applicant'
    model = Applicant
    pk_url_kwarg = 'aid'

    def get_queryset(self):
        return super().get_queryset().prefetch_related(
            Prefetch(
                'log_set', 
                queryset = Log.objects.select_related('equip').order_by('-date_apply'),
            ),
        )
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'inuse_list': self.object.log_set.filter(date_return=None),
        })
        return ctx

class ModelCreate(PermissionRequiredMixin, CreateView):
    permission_required = 'em.add_model'
    model = Model
    fields = ['name', 'date_buy', 'category', 'specification', 'si', 'pic']

    def get_success_url(self):
        return reverse_lazy('model_view', args=[self.object.id])

class ModelEdit(PermissionRequiredMixin, UpdateView):
    permission_required = 'em.change_model'
    model = Model
    fields = ['name', 'date_buy', 'category', 'specification', 'status', 'si', 'pic']
    pk_url_kwarg = 'mid'

    def get_success_url(self):
        return reverse_lazy('model_view', args=[self.object.id])
    
class EquipCreate(PermissionRequiredMixin, CreateView):
    permission_required = 'em.add_equip'
    model = Equip
    fields = ['name', 'prop_no', 'barcode', 'memo']
    template_name = 'em/model_form.html'

    def get_success_url(self):
        return reverse_lazy('model_view', args=[self.kwargs['mid']])
    
    def form_valid(self, form):
        form.instance.model_id = self.kwargs['mid']
        return super().form_valid(form)

class EquipEdit(PermissionRequiredMixin, UpdateView):
    permission_required = 'em.change_equip'
    model = Equip
    pk_url_kwarg = 'eid'
    fields = ['name', 'prop_no', 'barcode', 'memo', 'status']
    template_name = 'em/model_form.html'

    def get_success_url(self):
        return reverse_lazy('equip_view', args=[self.object.id])

class ApplicantCreate(PermissionRequiredMixin, CreateView):
    permission_required = 'em.add_applicant'
    model = Applicant
    fields = ['name', 'role', 'phone', 'email']
    template_name = 'em/model_form.html'

    def get_success_url(self):
        return reverse_lazy('applicant_view', args=[self.object.id])

class ApplicantEdit(PermissionRequiredMixin, UpdateView):
    permission_required = 'em.change_applicant'
    model = Applicant
    pk_url_kwarg = 'aid'
    fields = ['name', 'role', 'status', 'phone', 'email']
    template_name = 'em/model_form.html'

    def get_success_url(self):
        return reverse_lazy('applicant_view', args=[self.object.id])

class ApplicantLogCreate(PermissionRequiredMixin, CreateView):
    permission_required = 'em.add_log'
    model = Log
    fields = ['equip', 'date_apply']
    initial = {'date_apply': date.today()}

    def get_success_url(self):
        return reverse_lazy('applicant_view', args=[self.object.user_id])

    def form_valid(self, form):
        form.instance.user_id = self.kwargs['aid']
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        equip_list = Equip.objects.annotate(
            date_apply = Subquery(
                Log.objects.filter(
                    equip_id = OuterRef('id'),
                    date_return = None, 
                ).values('date_apply')[:1]
            ),
        ).select_related(
            'model',
        ).filter(
            model__status = 0,
            date_apply = None,
        ).order_by('-model', 'name')
        ctx['log_title'] = f'借用人：{Applicant.objects.get(id=self.kwargs["aid"]).name}'
        ctx['equip_list'] = equip_list
        ctx['model_list'] = Model.objects.filter(
            id__in=equip_list.values_list('model', flat=True).distinct()
        ).order_by('-id')
        return ctx
    
    def get_form(self):
        form = super().get_form()
        form.fields['equip'].widget.template_name = 'em/widgets/picker.html'
        return form

class EquipLogCreate(PermissionRequiredMixin, CreateView):
    permission_required = 'em.add_log'
    model = Log
    fields = ['user', 'date_apply']
    initial = {'date_apply': date.today()}

    def get_success_url(self):
        return reverse_lazy('equip_view', args=[self.object.equip_id])
    
    def form_valid(self, form):
        form.instance.equip_id = self.kwargs['eid']
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['log_title'] = f'借用設備：{Equip.objects.get(id=self.kwargs["eid"]).name}'
        ctx['applicant_list'] = Applicant.objects.order_by('status', 'role', 'name')
        return ctx

    def get_form(self):
        form = super().get_form()
        form.fields['user'].widget.template_name = 'em/widgets/picker.html'
        return form

class LogReturn(PermissionRequiredMixin, UpdateView):
    permission_required = 'em.change_log'
    model = Log
    fields = []
    pk_url_kwarg = 'lid'
    template_name = 'em/log_confirm_return.html'

    def get_success_url(self):
        if 'aid' in self.kwargs:
            return reverse_lazy('applicant_view', args=[self.object.user_id])
        return reverse_lazy('equip_view', args=[self.object.equip_id])
    
    def form_valid(self, form):
        form.instance.date_return = date.today()
        form.instance.author = self.request.user
        return super().form_valid(form)

class LogEdit(PermissionRequiredMixin, UpdateView):
    permission_required = 'em.change_log'
    model = Log
    pk_url_kwarg = 'lid'
    fields = ['user', 'equip', 'date_apply', 'date_return']

    def get_success_url(self):
        if 'aid' in self.kwargs:
            return reverse_lazy('applicant_view', args=[self.object.user_id])
        return reverse_lazy('equip_view', args=[self.object.equip_id])

    def get_form(self):
        form = super().get_form()
        form.fields['equip'].widget.template_name = 'em/widgets/picker.html'
        form.fields['user'].widget.template_name = 'em/widgets/picker.html'
        return form

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        equip_list = Equip.objects.annotate(
            date_apply = Subquery(
                Log.objects.filter(
                    equip_id = OuterRef('id'),
                    date_return = None, 
                ).values('date_apply')[:1]
            ),
        ).select_related(
            'model',
        ).filter(
            model__status = 0,
            date_apply = None,
        ).order_by('-model', 'id')
        ctx['equip_list'] = equip_list
        ctx['model_list'] = Model.objects.filter(
            id__in=equip_list.values_list('model', flat=True).distinct()
        ).order_by('-id')
        ctx['applicant_list'] = Applicant.objects.order_by('status', 'role', 'name')
        return ctx

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

class LogDelete(PermissionRequiredMixin, DeleteView):
    permission_required = 'em.delete_log'
    model = Log
    pk_url_kwarg = 'lid'

    def get_success_url(self):
        if 'aid' in self.kwargs:
            return reverse_lazy('applicant_view', args=[self.object.user_id])
        return reverse_lazy('equip_view', args=[self.object.equip_id])

class SIList(PermissionRequiredMixin, ListView):
    permission_required = 'em.view_si'
    model = SI
    ordering = ['name']

    def get_queryset(self):
        return super().get_queryset().prefetch_related('model_set')

class SIView(PermissionRequiredMixin, DetailView):
    permission_required = 'em.view_si'
    model = SI
    pk_url_kwarg = 'sid'

class SICreate(PermissionRequiredMixin, CreateView):
    permission_required = 'em.add_si'
    model = SI
    fields = '__all__'
    template_name = 'em/model_form.html'
    success_url = reverse_lazy('si_list')

class SIEdit(PermissionRequiredMixin, UpdateView):
    permission_required = 'em.change_si'
    model = SI
    fields = '__all__'
    pk_url_kwarg = 'sid'
    template_name = 'em/model_form.html'
    success_url = reverse_lazy('si_list')

class SIDelete(PermissionRequiredMixin, DeleteView):
    permission_required = 'em.delete_si'
    model = SI
    pk_url_kwarg = 'sid'
    success_url = reverse_lazy('si_list')

class InventoryList(PermissionRequiredMixin, ListView):
    permission_required = 'em.view_inventory'
    model = Inventory

class InventoryLogCreate(PermissionRequiredMixin, CreateView):
    permission_required = 'em.add_inventory'
    model = InventoryLog
    fields = []
    success_url = reverse_lazy('inventory_log_create')
    extra_context = {'title': '新增盤點紀錄'}
    template_name = 'em/inventory_form.html'

    def get_form(self):
        form = super().get_form()
        form.fields['barcode'] = forms.CharField(label='設備條碼', max_length=36, initial='')
        form.fields['barcode'].widget.attrs = {'autofocus': True}
        return form
    
    def form_valid(self, form):
        return HttpResponseRedirect(reverse_lazy('inventory_import'))
        try:
            inventory = Inventory.objects.get(year=date.today().year)
        except:
            messages.error(self.request, '找不到本年度盤點清冊，請先執行匯入功能！')
            return HttpResponseRedirect(reverse_lazy('inventory_import'))

        barcode = form.cleaned_data['barcode']
        equip = list(Equip.objects.filter(barcode=barcode).annotate(
            applicant = Subquery(Log.objects.filter(date_return__isnull=True, equip_id=OuterRef('id')).values('user__name')[:1]),
            date_apply = Subquery(Log.objects.filter(date_return__isnull=True, equip_id=OuterRef('id')).values('date_apply')[:1]),
        ).select_related('model'))
        if equip and equip[0].prop_no in inventory.invlist:
            equip = equip[0]
            form.instance.equip = equip
            form.instance.author = self.request.user
            log_list = InventoryLog.objects.filter(date_checked__year=date.today().year, equip=equip)
            item = inventory.invlist[equip.prop_no]
            applicant = f" <span uk-icon='arrow-right'></span> {equip.applicant}" if equip.applicant else ""
            item_info = f"""
<ul class="uk-child-width-1-1 uk-child-width-1-2@m" uk-grid>
    <li>
        <table class="uk-table uk-table-sm uk-table-divider uk-text-small">
            <tr>
                <th>財產編號<br>財產分號</th>
                <th>財產名稱<br>財產別名</th>
                <th>廠牌/型式<br>設備編號</th>
            </tr>
            <tr>
                <td>{item['財產編號']}<br>{item['財產分號']}</td>
                <td>{item['財產名稱']}<br>{item['財產別名']}</td>
                <td>{item['廠牌']} / {item['型式']}<br>{equip.name}{applicant}</td>
            </tr>
        </table>
        <div class="uk-card-title">第 {item['盤點頁數']} 頁<br/>財產分號 {item['財產分號']}</div>
    </li>
    <li><a href="{equip.model.pic.url}"><img src="{equip.model.pic.url}"></a></li>
</ul>"""
            if not log_list.exists():
                messages.success(self.request, item_info)
                return super().form_valid(form)
            log = log_list[0]
            log.author = self.request.user
            log.save()
            messages.success(self.request, item_info)
        else:
            messages.error(self.request, '條碼有誤！找不到相關的設備!'+barcode, 'danger')

        return HttpResponseRedirect(self.success_url)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        return ctx

class InventoryLogManualCreate(PermissionRequiredMixin, RedirectView):
    permission_required = 'em.add_inventory'

    def get_redirect_url(self, *args, **kwargs):
        equip = Equip.objects.get(id=self.kwargs['eid'])
        inv = InventoryLog(
            equip = equip, 
            author = self.request.user,             
        )
        inv.save()
        return reverse_lazy('inventory_view', args=[inv.date_checked.year])

class InventoryLogDelete(PermissionRequiredMixin, DeleteView):
    permission_required = 'em.del_inventory'
    model = InventoryLog
    pk_url_kwarg = 'ilid'

    def get_success_url(self):
        return reverse_lazy('inventory_view', args=[self.kwargs['year']])

class InventoryView(PermissionRequiredMixin, DetailView):
    permission_required = 'em.view_inventory'
    model = Inventory

    def get_object(self):
        return Inventory.objects.get(year=self.kwargs['year'])
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['year'] = self.kwargs['year']
        equip_list = Equip.objects.filter(barcode__isnull=False).annotate(
            applicant = Subquery(Log.objects.filter(date_return__isnull=True, equip_id=OuterRef('id')).values('user__name')[:1]),
            date_apply = Subquery(Log.objects.filter(date_return__isnull=True, equip_id=OuterRef('id')).values('date_apply')[:1]),
        )
        for equip in equip_list:
            if equip.prop_no in self.object.invlist:
                self.object.invlist[equip.prop_no]["equip"] = equip

        for inv in InventoryLog.objects.filter(date_checked__year=self.kwargs['year']).select_related('equip'):
            self.object.invlist[inv.equip.prop_no]["result"] = inv

        ctx['inventory_list'] = self.object.invlist
        return ctx


class InventoryImport(PermissionRequiredMixin, CreateView):
    permission_required = 'em.add_inventoryevent'
    model = Inventory
    extra_context = {'title': '上傳財產盤點清冊'}
    fields = ['year']

    def get_initial(self):
        return {
            'year': date.today().year,
        }

    def get_form(self):
        form = super().get_form()
        form.fields['inv_file'] = forms.FileField(label='盤點清冊試算表檔案')
        form.fields['inv_file'].widget.attrs = {'accept': '.xls, .xlsx'}
        return form

    def get_success_url(self):
        return reverse_lazy('inventory_view', args=[self.object.year])

    def form_valid(self, form):
        file = form.files['inv_file']
        ext = file.name.split(".")[-1]
        content = file.read()
        records = pyexcel.get_records(file_type=ext, file_content=content)
        equip_list = [equip for equip in Equip.objects.exclude(prop_no__regex='^[0-9]{9}$').exclude(prop_no__isnull=True)]
        inv_list = {}
        for rec in records:
            if rec['財產編號'] == '314010103':
                equip = list(filter(lambda e: e.prop_no == rec['財產編號'] + '-' + rec['財產分號'], equip_list))
                if equip:
                    equip[0].prop_no = "{}-{}".format(rec['財產編號'], rec['財產分號'])
                    equip[0].barcode = rec['條碼序號']
                    equip[0].save()
                    inv_list[equip[0].prop_no] = rec
                else:
                    print("X: ", rec['財產分號'], rec['財產名稱'], rec['財產別名'], rec['廠牌'], rec['型式'], rec['購置日期'])

        event = Inventory.objects.filter(year=form.cleaned_data['year'])

        if event.exists():
            self.object = event[0]
            self.object.invlist = inv_list
            self.object.save()
            return HttpResponseRedirect(self.get_success_url())

        form.instance.invlist = inv_list
        return super().form_valid(form)
