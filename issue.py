'''
A class represents for an issue in tracking system
'''

class Issue(object):
    """
    
    """
    def __init__(self, _id, title='', description='', attachments=[]):
        self._id = _id
        self.title = title
        self.description = description
        self.attachments = attachments
    
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