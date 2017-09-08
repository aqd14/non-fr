'''
Simple web scraper for getting data from issue tracking systems
'''

import requests
from bs4 import BeautifulSoup
from lxml import etree

import re

from issue import Issue

FIREFOX_URL_PREFIX = 'https://bugzilla.mozilla.org/show_bug.cgi?id='
MYLYN_URL_PREFIX = 'https://bugs.eclipse.org/bugs/show_bug.cgi?id='

def scrape_ff(_id):
    """
    Scrape Firefox issues
    """
    '''
    if len(ids) == 1:
        
    elif len(ids) == 2:
        
    else:
    '''
    url = FIREFOX_URL_PREFIX + str(_id)
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
    attachments_content = []
    attachments = soup.find(id='attachments')
    if attachments: # if there are some attachments
        attachments = attachments.find_all(class_='attach-desc')
        for attach in attachments:
            attachments_content.append(attach.a.text)
    
    # make an assumption that the reporter will make a more detailed description
    # with the first comment. Consider the first comment as a part of description
    # if the reporter is also the first commenter
    comments = soup.find_all(id=re.compile('^c\d+$'))
    if len(comments) > 0:
        reporter = soup.find(id='field-reporter').find(class_='fna').text
        # print('Reporter: %s' % reporter)
        first_commenter = comments[0].find(class_='fna').text
        # print('First commenter: %s' % first_commenter)
        
        if first_commenter == reporter: # get issue description if the first commenter is also reporter
            comment = comments[0].find(class_='comment-text').text
            # print('Comment: %s' % comment)
            description = comment
    
    print('Completed!\n')
    return Issue(str(_id), title, description, attachments_content)

def scrape_ml(_id):
    """ 
    Scrape Mylyn issues
    """
    url = MYLYN_URL_PREFIX + str(_id)
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
    attachments_content = []
    attachments = soup.find(id='attachment_table')
    if attachments: # if there is attachment
        attachments = attachments.find_all(id=re.compile("^a\d+$"))
        if len(attachments) > 1:
            for attach in attachments[1:]:
                attachments_content.append(attach.b.text)
    
    # make an assumption that the reporter will make a more detailed description
    # with the first comment. Consider the first comment as a part of description
    # if the reporter is also the first commenter
    comments = soup.find_all(class_='bz_comment')
    if len(comments) > 0:
        reporter = soup.find(id='bz_show_bug_column_2').find(class_='fn').text
        # print('Reporter: %s' % reporter)
        first_commenter = comments[0].find(class_='fn').text
        # print('First commenter: %s' % first_commenter)
        
        if first_commenter == reporter: # get issue description if the first commenter is also reporter
            comment = comments[0].find(class_='bz_comment_text').text
            # print('Comment: %s' % comment)
            description = comment
    
    print('Completed!\n')
    return Issue(str(_id), title, description, attachments_content)

def scrape(system, ids):
    """Scrape a list of issues given the id range.
    
    Args:
        system (str): The specified system. The prefix url will be determined given the system
                Currently support Firefox and Mylyn.
        ids (list): id range
        
    Return:
        issues: A list of scraped issues
        
    """
    issues = []
    system = system.upper()
    # If user want to scrape data within a range of ids
    if len(ids) == 2:
        for _id in range(ids[0], ids[1] + 1):
            if system == 'FIREFOX':
                issue = scrape_ff(_id)
            elif system == 'MYLYN':
                issue = scrape_ml(_id)
            else:
                raise RuntimeError('System is unsupported: ' + system)
            issues.append(issue)
    else:
        raise RuntimeError('Please specify the ids range you want to scrape!')
    
    return issues
   
def to_xml(f, system, issues):
    """ Write scraped issues to XML file
    
    File format:
    
    <root>
        <system>issue_system</system>
        <issues>
            <issue>
                <id>issue_id</id>
                <title>issue_title</title>
                <description>issue_description</description>
                <attachments>
                    <attach>attach_description_1</attach>
                    ....
                    <attach>attach_description_n</attach>
                </attachments>
            </issue>
            .....
            <issue>
                <id>issue_id</id>
                <title>issue_title</title>
                <description>issue_description</description>
                <attachments>
                    <attach>attach_description_1</attach>
                    ....
                    <attach>attach_description_n</attach>
                </attachments>
            </issue>
        </issues>
    </root>
    
    Args:
        f (file): the file to write
        system (str): scraped system
        issues (issue): list of issues
        
    Return:
        XML file
        
    """
    
    root = etree.Element("root")
    etree.SubElement(root, "system").text = system
    issues_e = etree.SubElement(root, "issues")
    
    for issue in issues:
        issue_e = etree.SubElement(issues_e, "issue")
        etree.SubElement(issue_e, "id").text = issue.get_id()
        etree.SubElement(issue_e, "title").text = issue.get_title()
        etree.SubElement(issue_e, "description").text = issue.get_description()
        attachments_e = etree.SubElement(issue_e, "attachments")
        # add attachment
        for at in issue.get_attachments():
            etree.SubElement(attachments_e, "attach").text = at
    
    # write to file
    tree = etree.ElementTree(element=root)
    tree.write(f, pretty_print=True, xml_declaration=True, encoding='utf-8')
    
system = 'Firefox'
id_range = [200001, 200010]
issues = scrape(system, id_range)
to_xml('data/issues.xml', system, issues)
