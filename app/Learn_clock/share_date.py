from config.env import QQ_ADMIN
clock_records = {}
admin_ids = [QQ_ADMIN]  # 初始管理员列表

def add_admin(user_id):
    """添加管理员"""
    if str(user_id) not in admin_ids:
        admin_ids.append(str(user_id))
        return True
    return False

def remove_admin(user_id):
    """移除管理员"""
    if str(user_id) in admin_ids:
        admin_ids.remove(str(user_id))
        return True
    return False

def is_admin(user_id):
    """检查是否是管理员"""
    return str(user_id) in admin_ids
