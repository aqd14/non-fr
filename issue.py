'''
A class represents for an issue in tracking system
'''

class Issue(object):
    """
    
    """
    def __init__(self, _id, title='', description='', attachments=[], comments = 0, commenters=0):
        self._id = _id
        self.title = title
        self.description = description
        self.attachments = attachments
        self.comments = comments
        self.commenters = commenters
    
    def __str__(self):
        representation = ['id: ' + self._id, 'title: ' + self.title, 'description: ' + self.description, 'attachments: ' + self.attachments]
        return '\n'.join(representation)
    
    def get_id(self):
        return self._id
    
    def get_title(self):
        return self.title
    
    def get_description(self):
        return self.description
    
    def get_attachments(self):
        return self.attachments
    
    def get_comments(self):
        return self.comments
    
    def get_commenters(self):
        return self.commenters