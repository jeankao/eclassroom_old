# -*- coding: UTF-8 -*-
from django.shortcuts import render
from django.apps import apps
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from forms import LoginForm, UserRegistrationForm, PasswordForm, RealnameForm, LineForm, SchoolForm, EmailForm
from account.models import Profile, PointHistory, Log, Message, MessagePoll, Visitor, VisitorLog
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.contrib.auth import authenticate, login
from django.utils import timezone
from django.utils.timezone import localtime
from django.views.generic import ListView, CreateView
from student.models import Enroll, Assistant
from django.contrib.auth.models import Group
from django.http import JsonResponse
from teacher.models import Classroom
# 判斷是否開啟事件記錄
def is_event_open(request):
        try:
            enrolls = Enroll.objects.filter(student_id=request.user.id)
            for enroll in enrolls:
                classroom = Classroom.objects.get(id=enroll.classroom_id)
                if classroom.event_open:
                    return True
        except:
            pass
        return False
      
# 判斷是否為任教學生
def is_student(user_id, request):
    classrooms = Classroom.objects.filter(teacher_id=request.user.id)
    for classroom in classrooms:
        if Enroll.objects.filter(classroom_id=classroom.id, student_id=user_id).exists(): 
            return True
    return False
    
# 判斷是否為本班同學
def is_classmate(user_id, classroom_id):
    return Enroll.objects.filter(student_id=user_id, classroom_id=classroom_id).exists()
      
# 網站首頁
def homepage(request):
    models = apps.get_models()
    row_count = 0
    for model in models:
        row_count = row_count + model.objects.count()
    users = User.objects.all()
    try :
        admin_user = User.objects.get(id=1)
        admin_profile = Profile.objects.get(user=admin_user)
    except ObjectDoesNotExist:
        admin_profile = ""
    return render_to_response('homepage.html', {'row_count':row_count, 'user_count':len(users), 'admin_profile': admin_profile}, context_instance=RequestContext(request))

# 使用者登入功能
def user_login(request):
        message = None
        test = ""
        if request.method == "POST":
                form = LoginForm(request.POST)
                if form.is_valid():
                        username = request.POST['username']
                        password = request.POST['password']
                        user = authenticate(username=username, password=password)
                        if user is not None:
                                if user.is_active:
                                        if user.id == 1:
                                            if user.first_name == "": 
                                                user.first_name = "管理員"
                                                user.save()
                                                # create Message
                                                title = "請修改您的姓名"
                                                url = "/account/realname"
                                                message = Message.create(title=title, url=url, time=timezone.now())
                                                message.save()                        
                    
                                                # message for group member
                                                messagepoll = MessagePoll.create(message_id = message.id,reader_id=1)
                                                messagepoll.save()                                                             
                                        # 登入成功，導到大廳
                                        login(request, user)
                                        # 記錄系統事件
                                        if is_event_open(request) :
                                            log = Log(user_id=request.user.id, event='登入系統')
                                            log.save()
                                        # 記錄訪客資訊
                                        admin_user = User.objects.get(id=1)
                                        try:
                                            profile = Profile.objects.get(user=admin_user)
                                        except ObjectDoesNotExist:
                                            profile = Profile(user=admin_user)
                                            profile.save()
                                        profile.visitor_count = profile.visitor_count + 1
                                        profile.save()
                                        
                                        year = localtime(timezone.now()).year
                                        month =  localtime(timezone.now()).month
                                        day =  localtime(timezone.now()).day
                                        date_number = year * 10000 + month*100 + day
                                        try:
                                            visitor = Visitor.objects.get(date=date_number)
                                        except ObjectDoesNotExist:
                                            visitor = Visitor(date=date_number)
                                        visitor.count = visitor.count + 1
                                        visitor.save()
                                        
                                        visitorlog = VisitorLog(visitor_id=visitor.id, user_id=user.id, IP=request.META.get('REMOTE_ADDR'))
                                        visitorlog.save()
                                        
                                        return redirect('dashboard')
                                else:
                                        message = "Your user is inactive"
                        else:
                            # 記錄系統事件
                            if is_event_open(request) :                            
                                log = Log(user_id=0, event='登入失敗')
                                log.save()                                
                            message = "無效的帳號或密碼!"
        else:
                form = LoginForm()
        return render_to_response('registration/login.html', {'test': test, 'message': message, 'form': form}, context_instance=RequestContext(request))

# 記錄登出
def suss_logout(request, user_id):
    # 記錄系統事件
    if is_event_open(request) :    
        log = Log(user_id=user_id, event='登出系統')
        log.save()    
    return redirect('/account/login/')
  
# 訊息
class MessageListView(ListView):
    context_object_name = 'messages'
    paginate_by = 20
    template_name = 'account/dashboard.html'

    def get_queryset(self):        
        query = []
        messagepolls = MessagePoll.objects.filter(reader_id=self.request.user.id).order_by('-message_id')
        for messagepoll in messagepolls:
            query.append([messagepoll, messagepoll.message])
        return query
        
# 註冊帳號                  
def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # Create a new user object but avoid saving it yet
            new_user = form.save(commit=False)
            # Set the chosen password                 
            new_user.set_password(
                form.cleaned_data['password'])
            # Save the User object
            new_user.save()
            profile = Profile(user=new_user)
            profile.save()
            # 記錄系統事件
            if is_event_open(request) :   
                log = Log(user_id=new_user.id, event='註冊帳號成功')
                log.save()                
        
            # create Message
            title = "請洽詢任課教師課程名稱及選課密碼"
            url = "/student/classroom/add"
            message = Message.create(title=title, url=url, time=timezone.now())
            message.save()                        
                    
            # message for group member
            messagepoll = MessagePoll.create(message_id = message.id,reader_id=new_user.id)
            messagepoll.save()               
            return render(request,
                          'account/register_done.html',
                          {'new_user': new_user})
    else:
        form = UserRegistrationForm()
    return render(request,
                  'account/register.html',
                  {'form': form})  
# 超級管理員可以查看所有帳號
class UserListView(ListView):
    context_object_name = 'users'
    paginate_by = 20
    template_name = 'account/user_list.html'
    
    def get_queryset(self):
        # 記錄系統事件
        if is_event_open(self.request) :           
            log = Log(user_id=1, event='管理員查看帳號')
            log.save()         
        queryset = User.objects.all().order_by('-id')
        return queryset
    
# Ajax 設為教師、取消教師
def make(request):
    user_id = request.POST.get('userid')
    action = request.POST.get('action')
    if user_id and action :
        user = User.objects.get(id=user_id)           
        try :
            group = Group.objects.get(name="teacher")	
        except ObjectDoesNotExist :
            group = Group(name="teacher")
            group.save()
        if action == 'set':            
            # 記錄系統事件
            log = Log(user_id=1, event=u'管理員設為教師<'+user.first_name+'>')
            log.save()                        
            group.user_set.add(user)
            # create Message
            title = "<" + request.user.first_name + u">設您為教師"
            url = "/teacher/classroom"
            message = Message.create(title=title, url=url, time=timezone.now())
            message.save()                        
                    
            # message for group member
            messagepoll = MessagePoll.create(message_id = message.id,reader_id=user_id)
            messagepoll.save()    
        else : 
            # 記錄系統事件
            if is_event_open(request) :               
                log = Log(user_id=1, event=u'取消教師<'+user.first_name+'>')
                log.save()              
            group.user_set.remove(user)  
            # create Message
            title = "<"+ request.user.first_name + u">取消您為教師"
            url = "/"
            message = Message.create(title=title, url=url, time=timezone.now())
            message.save()                        
                    
            # message for group member
            messagepoll = MessagePoll.create(message_id = message.id,reader_id=user_id)
            messagepoll.save()               
        return JsonResponse({'status':'ok'}, safe=False)
    else:
        return JsonResponse({'status':user.first_name}, safe=False)        

def message(request, messagepoll_id):
    messagepoll = MessagePoll.objects.get(id=messagepoll_id)
    messagepoll.read = True
    messagepoll.save()
    message = Message.objects.get(id=messagepoll.message_id)
    return redirect(message.url)
    
# 列出所有私訊
class LineListView(ListView):
    model = Message
    context_object_name = 'messages'
    template_name = 'account/line_list.html'    
    paginate_by = 20
    
    def get_queryset(self):
        # 記錄系統事件
        if is_event_open(self.request) :    
            log = Log(user_id=self.request.user.id, event='查看所有私訊')
            log.save()        
        queryset = Message.objects.filter(author_id=self.request.user.id, classroom_id=0-int(self.kwargs['classroom_id'])).order_by("-id")
        return queryset
        
# 列出同學以私訊
class LineClassListView(ListView):
    model = Enroll
    context_object_name = 'enrolls'
    template_name = 'account/line_class.html'   
    
    def get_queryset(self):
        # 記錄系統事件
        if is_event_open(self.request) :    
            log = Log(user_id=self.request.user.id, event='列出同學以私訊')
            log.save()        
        queryset = Enroll.objects.filter(classroom_id=self.kwargs['classroom_id']).order_by("seat")
        return queryset
        
    # 限本班同學
    def render_to_response(self, context):
        if not is_classmate(self.request.user.id, self.kwargs['classroom_id']):
            return redirect('/')
        return super(LineClassListView, self).render_to_response(context)            
                
#新增一個私訊
class LineCreateView(CreateView):
    model = Message
    context_object_name = 'messages'    
    form_class = LineForm
    template_name = 'account/line_form.html'     

    def form_valid(self, form):
        self.object = form.save(commit=False)
        user_name = User.objects.get(id=self.request.user.id).first_name
        self.object.title = u"[私訊]" + user_name + ":" + self.object.title
        self.object.author_id = self.request.user.id
        self.object.save()
        self.object.url = "/account/line/detail/" + str(self.object.id)
        self.object.classroom_id = 0 - int(self.kwargs['classroom_id'])
        self.object.save()
        # 訊息
        messagepoll = MessagePoll(message_id=self.object.id, reader_id=self.kwargs['user_id'], classroom_id=0-int(self.kwargs['classroom_id']))
        messagepoll.save()
        # 記錄系統事件
        if is_event_open(self.request) :            
            log = Log(user_id=self.request.user.id, event=u'新增私訊<'+self.object.title+'>')
            log.save()                
        return redirect("/account/line/"+self.kwargs['classroom_id'])       
        
    def get_context_data(self, **kwargs):
        context = super(LineCreateView, self).get_context_data(**kwargs)
        context['user_id'] = self.kwargs['user_id']
        context['classroom_id'] = self.kwargs['classroom_id']
        messagepolls = MessagePoll.objects.filter(reader_id=self.kwargs['user_id'],  classroom_id=0 - int(self.kwargs['classroom_id'])).order_by('-id')
        messages = []
        for messagepoll in messagepolls:
            message = Message.objects.get(id=messagepoll.message_id)
            if message.author_id == self.request.user.id :
                messages.append([message, messagepoll.read])
        context['messages'] = messages
        return context	 
        
# 查看私訊內容
def line_detail(request, message_id):
    message = Message.objects.get(id=message_id)
    try:
        messagepoll = MessagePoll.objects.get(message_id=message_id)
    except :
        pass
    return render_to_response('account/line_detail.html', {'message':message, 'messagepoll':messagepoll}, context_instance=RequestContext(request))


# 列出所有日期訪客
class VisitorListView(ListView):
    model = Visitor
    context_object_name = 'visitors'
    template_name = 'account/visitor_list.html'    
    paginate_by = 20
    
    def get_queryset(self):
        # 記錄系統事件
        if is_event_open(self.request) :
            if not self.request.user.is_authenticated():
                user_id = 0
            else :
                user_id = self.request.user.id
            log = Log(user_id=user_id, event='查看所有訪客')
            log.save()        
        queryset = Visitor.objects.all().order_by('-id')
        return queryset
        
# 列出單日日期訪客
class VisitorLogListView(ListView):
    model = VisitorLog
    context_object_name = 'visitorlogs'
    template_name = 'account/visitorlog_list.html'    
    paginate_by = 50
    
    def get_queryset(self):
        # 記錄系統事件
        visitor = Visitor.objects.get(id=self.kwargs['visitor_id'])
        if is_event_open(self.request) :    
            log = Log(user_id=self.request.user.id, event='查看單日訪客<'+str(visitor.date)+'>')
            log.save()        
        queryset = VisitorLog.objects.filter(visitor_id=self.kwargs['visitor_id']).order_by('-id')
        return queryset
        
    def render_to_response(self, context):
        if not self.request.user.is_authenticated():
            return redirect('/')
        return super(VisitorLogListView, self).render_to_response(context)

# 修改密碼
def password(request, user_id):
    if request.method == 'POST':
        form = PasswordForm(request.POST)
        if form.is_valid():
            user = User.objects.get(id=user_id)
            user.set_password(request.POST['password'])
            user.save()
            # 記錄系統事件
            if is_event_open(request) :               
                log = Log(user_id=request.user.id, event=u'修改<'+user.first_name+u'>密碼成功')
                log.save()                
            return redirect('homepage')
    else:
        form = PasswordForm()
        user = User.objects.get(id=user_id)

    return render_to_response('account/password.html',{'form': form, 'user':user}, context_instance=RequestContext(request))

# 修改他人的真實姓名
def adminrealname(request, user_id):
    if request.method == 'POST':
        form = RealnameForm(request.POST)
        if form.is_valid():
            user = User.objects.get(id=user_id)
            user.first_name =form.cleaned_data['first_name']
            user.save()
            # 記錄系統事件
            if is_event_open(request) :               
                log = Log(user_id=request.user.id, event=u'修改姓名<'+user.first_name+'>')
                log.save()                
            return redirect('/account/userlist/')
    else:
        user = User.objects.get(id=user_id)
        form = RealnameForm(instance=user)

    return render_to_response('form.html',{'form': form}, context_instance=RequestContext(request))
	
# 修改自己的真實姓名
def realname(request):
    if request.method == 'POST':
        form = RealnameForm(request.POST)
        if form.is_valid():
            user = User.objects.get(id=request.user.id)
            user.first_name =form.cleaned_data['first_name']
            user.save()
            # 記錄系統事件
            if is_event_open(request) :               
                log = Log(user_id=request.user.id, event=u'修改姓名<'+user.first_name+'>')
                log.save()                
            return redirect('/account/profile/'+str(request.user.id))
    else:
        user = User.objects.get(id=request.user.id)
        form = RealnameForm(instance=user)

    return render_to_response('form.html',{'form': form}, context_instance=RequestContext(request))

# 修改學校名稱
def adminschool(request):
    if request.method == 'POST':
        form = SchoolForm(request.POST)
        if form.is_valid():
            user = User.objects.get(id=request.user.id)
            user.last_name =form.cleaned_data['last_name']
            user.save()
            # 記錄系統事件
            if is_event_open(request) :               
                log = Log(user_id=request.user.id, event=u'修改學校名稱<'+user.last_name+'>')
                log.save()                
            return redirect('/account/profile/'+str(request.user.id))
    else:
        user = User.objects.get(id=request.user.id)
        form = SchoolForm(instance=user)

    return render_to_response('account/school.html',{'form': form}, context_instance=RequestContext(request))
    
# 修改信箱
def adminemail(request):
    if request.method == 'POST':
        form = EmailForm(request.POST)
        if form.is_valid():
            user = User.objects.get(id=user_id)
            user.email =form.cleaned_data['email']
            user.save()
            # 記錄系統事件
            if is_event_open(request) :               
                log = Log(user_id=request.user.id, event=u'修改信箱<'+user.first_name+'>')
                log.save()                
            return redirect('/account/profile/'+str(request.user.id))
    else:
        user = User.objects.get(id=request.user.id)
        form = EmailForm(instance=user)

    return render_to_response('account/email.html',{'form': form}, context_instance=RequestContext(request))    
# 記錄系統事件
class EventListView(ListView):
    context_object_name = 'events'
    paginate_by = 50
    template_name = 'account/event_list.html'

    def get_queryset(self):    
        user = User.objects.get(id=self.kwargs['user_id'])
        # 記錄系統事件
        if is_event_open(self.request) :           
            log = Log(user_id=self.request.user.id, event=u'查看個人事件<'+user.first_name+'>')
            log.save()       
        if self.request.GET.get('q') != None:
            queryset = Log.objects.filter(user_id=self.kwargs['user_id'], event__icontains=self.request.GET.get('q')).order_by('-id')
        else :
            queryset = Log.objects.filter(user_id=self.kwargs['user_id']).order_by('-id')
        return queryset
        
    def get_context_data(self, **kwargs):
        context = super(EventListView, self).get_context_data(**kwargs)
        q = self.request.GET.get('q')
        context.update({'q': q})
        return context	
        
    # 限本人 
    def render_to_response(self, context):
        if not is_student(self.kwargs['user_id'], self.request) and not self.request.user.id == int(self.kwargs['user_id']):
            return redirect('/')
        return super(EventListView, self).render_to_response(context)      
# 記錄系統事件
class EventAdminListView(ListView):
    context_object_name = 'events'
    paginate_by = 50
    template_name = 'account/event_admin_list.html'

    def get_queryset(self):    
        # 記錄系統事件
        log = Log(user_id=1, event=u'管理員查看系統事件')
        log.save()       
        if self.request.GET.get('q') != None:
            queryset = Log.objects.filter(event__icontains=self.request.GET.get('q')).order_by('-id')
        else :
            queryset = Log.objects.all().order_by('-id')
        return queryset
        
    def get_context_data(self, **kwargs):
        context = super(EventAdminListView, self).get_context_data(**kwargs)
        classrooms = Classroom.objects.all().order_by('-id')
        context['classrooms'] = classrooms
        q = self.request.GET.get('q')
        context.update({'q': q})
        return context	
        
    # 限管理員
    def render_to_response(self, context):
        if not self.request.user.id == 1 :
            return redirect('/')
        return super(EventAdminListView, self).render_to_response(context)      
        
# 記錄系統事件
class EventAdminClassroomListView(ListView):
    context_object_name = 'events'
    paginate_by = 50
    template_name = 'account/event_admin_classroom_list.html'

    def get_queryset(self):    
        # 記錄系統事件
        classroom = Classroom.objects.get(id=self.kwargs['classroom_id'])
        log = Log(user_id=1, event=u'管理員查看班級事件<'+classroom.name+'>')
        log.save()
        users = []
        enrolls = Enroll.objects.filter(classroom_id=self.kwargs['classroom_id'])
        for enroll in enrolls:
            if enroll.seat > 0 :
                users.append(enroll.student_id)
        if self.request.GET.get('q') != None:
            queryset = Log.objects.filter(user_id__in=users, event__icontains=self.request.GET.get('q')).order_by('-id')
        else :
            queryset = Log.objects.filter(user_id__in=users).order_by('-id')
        return queryset
        
    def get_context_data(self, **kwargs):
        context = super(EventAdminClassroomListView, self).get_context_data(**kwargs)
        q = self.request.GET.get('q')
        context.update({'q': q})
        classroom = Classroom.objects.get(id=self.kwargs['classroom_id'])
        context['classroom'] = classroom        
        return context	
        
    # 限管理員
    def render_to_response(self, context):
        if not self.request.user.id == 1:
            return redirect('/')
        return super(EventAdminClassroomListView, self).render_to_response(context)     
        