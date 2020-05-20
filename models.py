import peewee as pw

DB = pw.MySQLDatabase("spider", host="localhost", port=3306, user="root", password="123456")


class BaseModel(pw.Model):
    class Meta:
        database = DB


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


if __name__ == '__main__':
    DB.create_tables([Author, Answer, Topic])

