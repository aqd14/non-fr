'''
Simple web scraper for getting data from issue tracking systems
'''

import requests
from bs4 import BeautifulSoup
from lxml import etree

import os
import argparse
import re
import multiprocessing as mp
import time

from issue import Issue

FIREFOX_URL_PREFIX = 'https://bugzilla.mozilla.org/show_bug.cgi?id='
MYLYN_URL_PREFIX = 'https://bugs.eclipse.org/bugs/show_bug.cgi?id='
LUCENE_URL_PREFIX = 'https://issues.apache.org/jira/browse/LUCENE-'

DUPLICATED_ISSUES = ["RESOLVED DUPLICATE", "VERIFIED DUPLICATE"] # ignore duplicate issues

MINIMUM_COMMENTS = 1 # minimum number of comments in an issue to be considered as an active discussion
MINIMUM_COMMENTERS = 1 # minimum number of commenters in an issue to be considered as an active discussion

firefox_attributes = {
    'status-id':'field-value-status_summary', 'title-id':'field-value-short_desc',
    'attachment-id':'attachments', 'attachment-regex':'^attach-desc$',
    'comment-regex':'^c\d+$', 'reporter-id':'field-reporter', 'reporter-class':'fna',
    'commenter-class':'fna', 'comment-text-class':'comment-text'
}

mylyn_attributes = {
    'status-id':'bz_field_status', 'title-id':'short_desc_nonedit_display',
    'attachment-id':'attachment_table', 'attachment-regex':'^bz_contenttype+$',
    'comment-regex':'^c\d+$', 'reporter-id':'bz_show_bug_column_2', 'reporter-class':'vcard',
    'commenter-class':'fn', 'comment-text-class':'bz_comment_text'
}

lucene_attributes = {
    'status-id':'type-val', 'title-id':'summary-val', 'description-id':'description-val', 'comment-regex':'^comment-\d+$'
}

def scrape_issue(url_prefix, _id, attributes):
    """Scrape Mylyn or Firefox issues (They share HTML structure)
    
    Parameters
    ----------
    url_prefix : string
        Issue tracking system URL prefixx
        
    _id : string
        Issue id
        
    attributes : dictionary
        Contains all HTML attributes needed to scrape data
    
    Returns
    -------
    issue : an Issue instance
    """
    # extract necessary html attributes from dictionary
    status_id = attributes['status-id']
    title_id = attributes['title-id']
    attachment_id = attributes['attachment-id']
    attachment_regex = attributes['attachment-regex']
    comment_regex = attributes['comment-regex']
    reporter_id = attributes['reporter-id']
    reporter_class = attributes['reporter-class']
    commenter_class = attributes['commenter-class']
    comment_text_class = attributes['comment-text-class']
    
    url = url_prefix + str(_id)
    print('Scraping url: %s' % url)
    
    try:
        result = requests.get(url)
        # Can't access the url
        if result.status_code != 200:
            print('Can\'t access url!')
            return
        c = result.content
        soup = BeautifulSoup(c, 'lxml')
        # check if the issue is duplicate
        status = soup.find(id=status_id).text
        status = ' '.join(status.split())
        if status in DUPLICATED_ISSUES:
            print('[{0}] Duplicated issue!'.format(_id))
            return None
        
        if 'bugzilla.mozilla.org' in url_prefix:
            importance = soup.find(id='field-value-bug_severity').text
        elif 'https://bugs.eclipse.org' in url_prefix:
            importance = soup.find(id='bz_show_bug_column_1').find('table').find_all('tr')[8].text
        else: # invalid url
            return None
        
        importance = ' '.join(importance.split())
        if 'enhancement' not in importance: # only retrieve requirements (with enhancement)
            print('[{0}] Not requirement - {1}\n'.format(_id, importance))
            return None
        
        title = soup.find(id=title_id).text
        # print(title)
        description = ""
        # make an assumption that the reporter will make a more detailed description
        # with the first comment. Consider the first comment as a part of description
        # if the reporter is also the first commenter
        comments = soup.find_all(id=re.compile(comment_regex))
        if len(comments) > MINIMUM_COMMENTS: # the scraped issue should have a certain number of comments to be considered active
            # Count number of commenters participating in the discussion
            commenters = count_commenters(_id, comments, ('span', {'class':commenter_class}))
            if commenters is None:
                return None
            
            reporter = soup.find(id=reporter_id).find(class_=reporter_class).text
            reporter = reporter.replace('\n', '').strip() # re-format reporter name
            # print('Reporter: %s' % reporter)
            first_commenter = comments[0].find(class_=commenter_class).text
            first_commenter = first_commenter.replace('\n', '').strip() # re-format commenter name
            
            if first_commenter == reporter: # get issue description if the first commenter is also reporter
                comment = comments[0].find(class_=comment_text_class).text
                # print('Comment: %s' % comment)
                description = ' '.join(comment.split())
        else:
            print('[{0}] Issue has only {1} comments\n'.format(_id, len(comments)))
            return None
                    
        # Attachments description might reveal some important information about the issue
        # Include all obsolete attachments
        attachments_content = []
        attachments = soup.find(id=attachment_id)
        if attachments: # if there is attachment
            attachments = attachments.find_all(class_=re.compile(attachment_regex))
            if len(attachments) > 1:
                for attach in attachments[1:]:
                    if 'bugzilla.mozilla.org' in url_prefix:
                        attachments_content.append(' '.join(attach.a.text.split()))
                    elif 'https://bugs.eclipse.org' in url_prefix:
                        attachments_content.append(' '.join(attach.b.text.split()))

    except Exception as err: # an unexpected exception happened. sometimes due to invalid authority access
        print('[{0}] Exception happened! {1}\n'.format(_id, err))
        return None
    
    print('[{0}] Completed!\n'.format(_id))
    return Issue(str(_id), title, description, attachments_content, len(comments), len(commenters))

def scrape_lucene(url_prefix, _id, attributes):
    """Scrape LUCENE issues
    
    Parameters
    ----------
    url_prefix : string
        Issue tracking system URL prefixx
        
    _id : string
        Issue id
        
    attributes : dictionary
        Contains all HTML attributes needed to scrape data
    
    Returns
    -------
    issue : an Issue instance
    """
    
    status_id = attributes['status-id']
    title_id = attributes['title-id']
    description_id = attributes['description-id']
    comment_regex = attributes['comment-regex']
    
    url = url_prefix + str(_id)
    print('Scraping url: %s' % url)

    try:
        result = requests.get(url)
        if result.status_code != 200:
            print('Can\'t access URL!')
        
        soup = BeautifulSoup(result.content, 'lxml')
        status = soup.find(id=status_id).text
        status = ' '.join(status.split())
        if status != 'New Feature' and status != 'Improvement': # not a requirement
            print('[{0}] Not requirement - {1}\n'.format(_id, status))
            return None
        
        # Only accept issue that contains a certain number of comments
        comments = soup.find_all(id=re.compile(comment_regex))
        if len(comments) < MINIMUM_COMMENTS:
            print('[{0}] Issue has only {1} comments!\n'.format(_id, len(comments)))
            return None
        else:
            print('[{0}] Issue has {1} comments!\n'.format(_id, len(comments)))
        # Count number of commenters participating in the discussion
        commenters = count_commenters(_id, comments, ('a', {'class':'user-hover user-avatar'}))
        if commenters is None:
            return None
            
        title = ' '.join(soup.find(id=title_id).text.split())
        description = ' '.join(soup.find(id=description_id).text.split())
    except Exception as err:
        print('[{0}] Exception happened! {1}\n'.format(_id, err))
        return None
    
    print('[{0}] Completed!\n'.format(_id))
    return Issue(str(_id), title, description, [], len(comments), len(commenters))

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
    for i in ids:
        if system == 'FIREFOX':
            issue = scrape_issue(url_prefix=FIREFOX_URL_PREFIX, _id=i, attributes=firefox_attributes)
        elif system == 'MYLYN':
            issue = scrape_issue(url_prefix=MYLYN_URL_PREFIX, _id=i, attributes=mylyn_attributes)
        elif system == 'LUCENE':
            issue = scrape_lucene(url_prefix=LUCENE_URL_PREFIX, _id=i, attributes=lucene_attributes)
        else:
            raise RuntimeError('System is unsupported: ' + system)
        
        if issue is not None:
            issues.append(issue)
    return issues

def count_commenters(_id, comments, attributes):
    # Count number of commenters participating in the discussion
    commenters = dict()
    for comment in comments:
        c = comment.find(attributes[0], attrs=attributes[1]).text
        commenters[c] = commenters.get(c, 0) + 1
    
    if (len(commenters) < MINIMUM_COMMENTERS):
        print('[{0}] Issue has only {1} comments!\n'.format(_id, len(commenters)))
        return None
    else:
        print('[{0}] Issue has {1} commenters!\n'.format(_id, len(commenters)))
    
    return commenters

def multiprocess_scrape(system, ids, num_processes):
    """Use a pool of workers to speed up scraping process
    
    Arguments:
        system: an open-source system (Firefox or Mylyn)
        ids: a list of id ranges
        num_processes: number of desired parallel processes
    
    Returns:
        a list of scraped data storing in Issue objects
    """
    pool = mp.Pool(processes=num_processes)
    results = [pool.apply_async(scrape, args=(system, range(id_range[0], id_range[1]))) for id_range in ids]
    # ensure that all processes in the pool were terminated and resources were freed
    pool.close() 
    pool.join()
    
    l = []
    [l.append(r.get()) for r in results]
    
    # flat out multiple list into one
    issues = [item for sublist in l for item in sublist]
    
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
                <comments>number_of_comments</comments>
                <commenters>number_of_commenter</commenters>
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
                <comments>number_of_comments</comments>
                <commenters>number_of_commenter</commenters>
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
        
        etree.SubElement(issue_e, "comments").text = str(issue.get_comments())
        etree.SubElement(issue_e, "commenters").text = str(issue.get_commenters())
    # write to file
    tree = etree.ElementTree(element=root)
    tree.write(f, pretty_print=True, xml_declaration=True, encoding='utf-8')
 
def split_range(l, n):
    """Split a list into n-equal ranges
    
    Arguments:
        l: the list to be partitioned
        n: number of sub-ranges
        
    Returns:
        a list of equal ranges
    """
    
    if len(l) != 2:
        raise RuntimeError('Splited list should have length 2!\n')
    
    if l[0] > l[1]:
        raise RuntimeError('The first item in list should be smaller one - {0} > {1}\n'.format(l[0], l[1]))
    
    range_list = []
    range_diff = (l[1] - l[0])/n
    for i in range(n):
        range_list.append([l[0]+range_diff*i, l[0]+range_diff*(i+1)-1])
        
    return range_list

def main():
    # argurment parser
    parser = argparse.ArgumentParser('python scraper.py <system> <from-id> <to-id> <num-processes> <--filepath>', description='Running scraper.')
    # positional arguments
    parser.add_argument('system', type=str, help='An open-source system. Can be either Firefox, Mylyn or Lucene')
    parser.add_argument('from-id', type=int, help='Starting id.')
    parser.add_argument('to-id', type=int, help='Ending id.')
    parser.add_argument('num-processes', type=int, help='Number of processes running to scrape data.')
    # optional arguments
    parser.add_argument('--filepath', type=str, help='filepath to generated xml file.')
    
    _args = vars(parser.parse_args())
#     _args = vars(parser.parse_args(['Mylyn', '500000', '500100', '10', '--filepath=issues.xml']))
    
    ids = split_range([_args['from-id'], _args['to-id']], _args['num-processes'])
    issues = multiprocess_scrape(_args['system'], ids, _args['num-processes'])

    print('There are {0} requirements are valid!'.format(len(issues)))
    # write scraped issues to xml file
    filepath = _args.get('filepath', -1)
    if filepath == -1 or filepath is None: # user didn't input filepath, use current date time to make unique file name
        # currentDT = time.strftime("%m-%d-%Y %H-%M-%S")
        additional = str(_args['from-id']) + "-" + str(_args['to-id'])
        filepath = _args['system'] + '-' + additional + '.xml'
        filepath = os.path.join('data', filepath)
        
    print(filepath)
    to_xml(filepath, _args['system'], issues)

if __name__ == '__main__':
    main()
