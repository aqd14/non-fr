'''
A class represents for an issue in tracking system
'''
from lxml.html.builder import TITLE

class Issue(object):
    """
    
    """
    def __init__(self, id, title, description, attachments):
        self.id = id
        self.title = title
        self.description = description
        self.attachments = attachments
    
    def __str__(self):
        representation = ['id: ' + str(self.id), 'title: ' + self.title, 'description: ' + self.description, 'attachments: ' + self.attachments]
        return '\n'.join(representation)
