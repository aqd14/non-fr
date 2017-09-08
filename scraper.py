'''
Simple web scraper for getting data from issue tracking systems
'''

import requests
from bs4 import BeautifulSoup

import re

from issue import Issue

FIREFOX_URL_PREFIX = 'https://bugzilla.mozilla.org/show_bug.cgi?id='
MYLYN_URL_PREFIX = 'https://bugs.eclipse.org/bugs/show_bug.cgi?id='

def scrape_ff(id):
    """
    Scrape Firefox issues
    """
    '''
    if len(ids) == 1:
        
    elif len(ids) == 2:
        
    else:
    '''
    url = FIREFOX_URL_PREFIX + str(id)
    print('Scraping url: %s' % url)
    result = requests.get(url)
    
    # Can't access the url
    if result.status_code != 200:
        print('Can\'t access url!')
        return
    c = result.content
    soup = BeautifulSoup(c, 'lxml')
    # print(soup.header)
    # bs = soup.find_all('h1')
    # print(bs)
    title = soup.find(id="field-value-short_desc").text
    # print(title)
    description = ''
    
    # Attachments description might reveal some important information about the issue
    attachments_content = ""
    attachments = soup.find(id='attachments').find_all(class_='attach-desc')
    for attach in attachments:
        attachments_content += attach.a.text + '\n'
    
    # make an assumption that the reporter will make a more detailed description
    # with the first comment. Consider the first comment as a part of description
    # if the reporter is also the first commenter
    comments = soup.find_all(class_='change-set')
    if len(comments) > 0:
        reporter = soup.find(id='field-reporter').find(class_='fna').text
        # print('Reporter: %s' % reporter)
        first_commenter = comments[0].find(class_='fna').text
        # print('First commenter: %s' % first_commenter)
        
        if reporter is first_commenter:
            comment = comments[0].find(class_='comment_text').text
            # print('Comment: %s' % comment)
            description = comment
    
    return Issue(id, title, description, attachments_content)

def scrape_ml(id):
    """ 
    Scrape Mylyn issues
    """
    url = MYLYN_URL_PREFIX + str(id)
    print('Scraping url: %s' % url)
    result = requests.get(url)
    # Can't access the url
    if result.status_code != 200:
        print('Can\'t access url!')
        return
    c = result.content
    soup = BeautifulSoup(c, 'lxml')
    title = soup.find(id='short_desc_nonedit_display').text
    # print(title)
    description = ""
    
    # Attachments description might reveal some important information about the issue
    # Include all obsolete attachments
    attachments_content = ""
    attachments = soup.find(id='attachment_table').find_all(id=re.compile("^a\d+$"))
    if len(attachments) > 1:
        for attach in attachments[1:]:
            attachments_content += attach.b.text + '\n'
    
    # make an assumption that the reporter will make a more detailed description
    # with the first comment. Consider the first comment as a part of description
    # if the reporter is also the first commenter
    comments = soup.find_all(class_='bz_comment')
    if len(comments) > 0:
        reporter = soup.find(id='bz_show_bug_column_2').find(class_='fn').text
        # print('Reporter: %s' % reporter)
        first_commenter = comments[0].find(class_='fn').text
        # print('First commenter: %s' % first_commenter)
        
        if reporter is first_commenter:
            comment = comments[0].find(class_='bz_comment_text').text
            # print('Comment: %s' % comment)
            description = comment
    
    return Issue(id, title, description, attachments_content)
   
def to_xml(issues):
    for issue in issues:
        to_xml(issue)

iss_ml = scrape_ml(201154)
print(iss_ml)
iss_ff = scrape_ff(200001)
print(iss_ff)
