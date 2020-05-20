# python-csdn-reptile
基于python的爬虫，用于爬取csdn论坛的信息

我们会将爬取到的信息存入mysql数据库，采用的对象关系映射框架为peewee

爬取的信息主要分为三个模块：帖子、用户、回帖信息

其中帖子的结构如下代码所示：
```python
class Topic(BaseModel):
    """
    "帖子" 对象关系映射
    """
    topic_id = pw.IntegerField(primary_key=True)  # 帖子的主键id
    topic_title = pw.CharField()  # 帖子的标题
    topic_content = pw.TextField(default="")  # 帖子的内容
    author_uuid = pw.CharField()  # 发帖者uuid
    latest_answerer_uuid = pw.CharField()  # 最新的回帖者uuid
    answer_nums = pw.IntegerField(default=0)  # 回帖数
    click_nums = pw.IntegerField(default=0)  # 点击量
    praised_nums = pw.IntegerField(default=0)  # 点赞数
    score = pw.IntegerField(default=0)  # 悬赏分
    status = pw.CharField()  # 已结/未结/满意
    end_percentage = pw.CharField(default="")  # 结帖率
    create_time = pw.DateField()  # 创建时间
    update_time = pw.DateField()  # 修改时间
```

用户的结构如下代码所示：
```python
class Author(BaseModel):
    """
    "用户实体" 对象关系映射
    """
    author_uuid = pw.CharField(primary_key=True)  # 用户的主键id
    name = pw.CharField()  # 用户的nickname
    desc = pw.CharField(null=True)  # 用户自定义描述
    rank = pw.CharField(default="")  # 全站排名
    end_topic_percentage = pw.CharField(default="") # 结贴率
    original_blog_nums = pw.CharField(default=0) # 原创博文数
    post_question_nums = pw.CharField(default=0)  # 提问数
    answer_question_nums = pw.CharField(default=0)  # 回答数
    post_topic_nums = pw.CharField(default="")  # 发帖数
    answer_topic_nums = pw.CharField(default="") # 回帖数
    follower_nums = pw.CharField(default=0)  # 粉丝数
    following_nums = pw.CharField(default=0)  # 关注数
```

回帖信息的结构如下代码所示：
```python
class Answer(BaseModel):
    """
    "回帖" 对象关系映射
    """
    answer_id = pw.CharField(primary_key=True)  # 回帖的主键id
    topic_id = pw.IntegerField()  # 关联的帖子主键id
    author_uuid = pw.CharField()  # 回帖的作者uuid
    answer_content = pw.TextField(default="")  # 回帖的内容
    create_time = pw.DateTimeField()  # 回帖时间
    praised_nums = pw.IntegerField(default=0)  # 回帖点赞数
```



下面是成功爬取数据库后的部分示例数据：

![image-20200520180632058](C:\Users\WHL\AppData\Roaming\Typora\typora-user-images\image-20200520180632058.png)



### 爬取流程

首先，我们会去到某个论坛下，爬取帖子的部分信息，比如帖子标题、创建时间、点击量等。

但问题在于，帖子的内容、点赞数、结帖率，这部分信息必须要进入到该帖子后才能够成功获取。因此，我们要爬取完整的帖子信息，就至少需要与服务器进行两次两次交互。一次交互用于爬取帖子标题等信息，另一次交互用于爬取帖子内容等信息。

在确保我们的帖子能够正常爬取时，我们还需要爬取回帖的信息。

爬取回帖信息时，针对每一个回帖的用户，我们还会爬取与其相关的用户信息。



### 性能优化

考虑到最初的爬虫程序是通过单线程来执行的，效率低下。因此这里通过两种不同的方式来实现多线程爬虫：

* 线程池

  将三个模块的爬取任务交给线程池，由线程池内部分配线程来完成这些任务。

  这种方式相对更优，毕竟可以根据自己的操作系统的CPU个数指定工作线程的数量。

* 阻塞队列（生产者消费者模型 + 多线程处理）

  当线程A在爬取帖子相关的信息时，将获取到的帖子url放到阻塞队列，让负责处理回帖信息的线程B去获取并处理。

  同样地，线程B也会将用户url放到阻塞队列，让负责处理用户信息的线程C去获取并处理。

