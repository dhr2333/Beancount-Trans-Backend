import json
from datetime import datetime

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views import View
from rest_framework import generics

from .models import Department
from .models import Users
from .serializers import UserSerializer


# Create your views here.


def indexUsers(request):
    # 浏览用户信息
    try:
        ulist = Users.objects.all()
        context = {"userslist": ulist}
        return render(request, "myapp/users/index.html", context)
    except:
        return HttpResponse("没有找到用户信息")


def addUsers(request):
    # 加载添加用户信息表单
    try:
        ulist = Users.objects.all()
        context = {"userslist": ulist}
        return render(request, "myapp/users/add.html", context)
    except:
        return HttpResponse("没有找到用户信息")


def insertUsers(request):
    # 执行用户信息添加
    try:
        ob = Users()
        # 从表单中获取要添加的信息并封装到ob对象中
        ob.name = request.POST['name']
        ob.age = request.POST['age']
        ob.phone = request.POST['phone']
        ob.save()
        context = {"info": "添加成功"}
    except:
        context = {"info": "添加失败"}
    return render(request, "myapp/users/info.html", context)


def delUsers(request, uid=None):
    # 执行用户信息删除
    try:
        ob = Users.objects.get(id=uid)  # 获取到删除的数据
        ob.delete()
        context = {"info": "删除成功"}
    except:
        context = {"info": "删除失败"}
    return render(request, "myapp/users/info.html", context)


def editUsers(request, uid=0):
    # 加载用户信息修改表单
    try:
        ob = Users.objects.get(id=uid)  # 获取到修改的数据
        context = {"users": ob}
        return render(request, "myapp/users/edit.html", context)
    except:
        context = {"users": "没有找到要修改的数据"}
    return render(request, "myapp/users/edit.html", context)


def updateUsers(request):
    # 执行用户信息修改
    try:
        uid = request.POST['id']
        ob = Users.objects.get(id=uid)
        # 从表单中获取要添加的信息并封装到ob对象中
        ob.name = request.POST['name']
        ob.age = request.POST['age']
        ob.phone = request.POST['phone']
        ob.addtime = datetime.now()
        ob.save()
        context = {"info": "修改成功"}
    except:
        context = {"info": "修改失败"}
    return render(request, "myapp/users/info.html", context)


def demo_view(request):
    response = HttpResponse('ok')
    response.set_cookie('name', 'python', max_age=3600)
    print(request.COOKIES.get('name'))
    return response


def session_demo(request):
    """session 读写操作"""
    request.session['name'] = 'zhangsan'  # 设置,session依赖与cookie
    print(request.session.get('name'))  # 读写
    return HttpResponse('session_demo')


def tpl(request):
    context = {"info": "修改成功", "n2": [1, 2, 3, 4]}
    # book = Department(title="销售部")
    # book.save()
    book = Department.objects.get(id=6)
    book2 = Department.objects.all()
    book1 = Department.objects.filter(id=6)
    for obj in book2:
        print(obj)
    print(book, book1, book2)  # book1和book2都是QuerySet对象
    book3 = Department.objects.get(id=6)
    book3.title = "技术部"
    book3.save()

    # book.delete()
    return render(request, "myapp/users/tpl.html", context)


class UserListView(View):
    """列表视图"""

    def get(self, request):
        # 1. 查询所有用户模型
        users = Users.objects.all()
        # 2. 将用户模型转换成字典并追加为列表
        user_list = []
        for user in users:
            user_dict = {
                "id": user.id,
                "name": user.name,
                "age": user.age,
                "phone": user.phone
            }
            user_list.append(user_dict)
        # 3. 以列表形式进行响应需要添加safe=False
        return JsonResponse(user_list, safe=False)

    def post(self, request):
        # 1. 获取前端传入的请求体数据(JSON)
        # 将bytes类型的json字符串转换成json_str
        # 利用json.load将json字符串转换成json(字典/列表)
        json_str_bytes = request.body
        print("request.body:", json_str_bytes)
        json_str = json_str_bytes.decode()  # decode()用于将已编码的字符串转换为Unicode字符串
        print("json_str_bytes.decode()", json_str)
        user_dict = json.loads(json_str)
        print("json.loads(json_str)", user_dict)
        # 2. 创建模型对象并保存（将字典转换成模型并存储，反序列化）
        user = Users(name=user_dict['name'],
                     age=user_dict["age"],
                     phone=user_dict["phone"])
        user.save()
        # 3. 把新增的模型转换成字典（序列化）
        user_dict = {
            'id': user.id,
            "name": user.name,
            "age": user.age,
            "phone": user.phone,
            "addtime": user.addtime if user.addtime else "",
        }
        # 4. 响应（按照规范需要返回新增的数据，201状态码）
        return JsonResponse(user_dict, status=201)


class UserDetailView(View):
    def get(self, request, id):
        try:
            user = Users.objects.get(id=id)
        except Users.DoesNotExist:
            return HttpResponse({"message": "查询数据不存在"}, status=404)
        user_dict = {
            "id": user.id,
            "name": user.name,
            "age": user.age,
            "phone": user.phone
        }
        return JsonResponse(user_dict)

    def put(self, request, id):
        # 1. 查询要修改的模型对象
        try:
            user = Users.objects.get(id=id)
        except Users.DoesNotExist:
            return HttpResponse({"message": "查询数据不存在"}, status=404)
        # 2. 获取前端传入的请求体数据
        user_dict = json.loads(request.body.decode())
        # 3. 格式化
        user.name = user_dict["name"]
        user.age = user_dict["age"]
        user.phone = user_dict["phone"]
        # 4. 为模型赋新值并调用save进行修改操作
        user.save()
        # 5. 将修改后的模型转换为字典
        user_dict = {
            'id': user.id,
            "name": user.name,
            "age": user.age,
            "phone": user.phone,
            "addtime": user.addtime if user.addtime else "",
        }
        # 6. 响应
        return JsonResponse(user_dict, status=201)

    def delete(self, request, id):
        try:
            user = Users.objects.get(id=id)
        except Users.DoesNotExist:
            return HttpResponse({"message": "要删除的数据不存在"}, status=404)
        user.delete()
        return HttpResponse(status=204)  # 删除成功返回204状态码


# Create your views here.
# def upload_file(request):
#     # 请求方法为POST时,进行处理;
#     if request.method == "POST":
#         # 获取上传的文件,如果没有文件,则默认为None;
#         User = request.POST.get("user")
#         Age = request.POST.get("age")
#         File = request.FILES.get("file", None)
#         if File is None:
#             return HttpResponse("no files for upload!")
#         else:
#             # 打开特定的文件进行二进制的写操作;
#             file_path = os.path.join("collectedstatic", File.name)
#             with open(file_path, 'wb+') as f:
#                 # 分块写入文件;
#                 for chunk in File.chunks():
#                     f.write(chunk)
#             # 数据库操作
#             upload = Upload(name=User, age=Age, file_path=file_path)
#             upload.save()
#             return HttpResponse("upload over!")
#     else:
#         latest_question_list = "文件还未上传"
#         image = "127.0.0.1:8002/" + Upload.objects.get(id=3).file_path
#         context = {
#             "latest_question_list": latest_question_list,
#             "image": image,
#         }
#         return render(request, 'translate/test.html', context)
#
#
# def image_view(request):
#     if request.method == "POST":
#         form = MyForm(request.POST, request.FILES)
#         if form.is_valid():
#             form.save()
#             return HttpResponse("success_page")
#         return HttpResponse("数据验证失败")
#     else:
#         form = MyForm()
#         mymodels = MyCmodel.objects.all()
#         file_path = os.path.join("media", str(mymodels[0].image))
#         print(file_path)
#         context = {"form": form, "mymodels": mymodels, "file_path": file_path}
#         print(mymodels[0].image)
#         return render(request, 'translate/image.html', context)

class UserList(generics.ListCreateAPIView):
    queryset = Users.objects.all()
    serializer_class = UserSerializer


class UserDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Users.objects.all()
    serializer_class = UserSerializer
