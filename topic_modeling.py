# Topic modeling with scikit-learn
# Some methods are inspired from scikit-learn tutorials
# topic_modeling.py

from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import NMF, LatentDirichletAllocation
import numpy as np

from lxml import etree

import os

from issue import Issue
from scraper import multiprocess_scrape, split_range, to_xml, scrape

n_features = 1000
# n_components = 10
# n_top_words = 10


WORD_LIST = {
    'efficiency' : os.path.join('wordlists', 'exp3', 'efficiency.txt'),
    'functionality' : os.path.join('wordlists', 'exp3', 'functionality.txt'),
    'maintainability' : os.path.join('wordlists', 'exp3', 'maintainability.txt'),
    'portability' : os.path.join('wordlists', 'exp3', 'portability.txt'),
    'reliability' : os.path.join('wordlists', 'exp3', 'reliability.txt'),
    'usability' : os.path.join('wordlists', 'exp3', 'usability.txt'),
}

def unique_list(l):
    """Remove duplicate term from a list
    
    Parameters
    ----------
    l : list
        A list potentially contains duplicate terms
        
    Returns
    ulist : list
        A list without unique terms
    """
    ulist = []
    for item in l:
        if item not in ulist:
            ulist.append(item)
    return ulist

def filter_issues(issues, comment_std_dev=0, commenter_std_dev=0):
    """Filter issues with number of comments and commenters higher than average
    
    Parameters
    ----------
    issues : list of Issue
    
    std_dev : standard deviation
    
    Returns
    -------
    filtered_issues
    """
    
    total_comments = 0;
    total_commenters = 0;
    for issue in issues:
        total_comments += issue.get_comments()
        total_commenters += issue.get_commenters()
    
    avg_comment = total_comments/len(issues)
    avg_commenter = total_commenters/len(issues)
    
    print('Average comments: {0}'.format(avg_comment))
    print('Average commenters: {0}'.format(avg_commenter))
    
    filtered_issues = []
    
    for issue in issues:
        if issue.get_comments() >= (avg_comment+comment_std_dev) and issue.get_commenters() >= (avg_commenter + commenter_std_dev):
            filtered_issues.append(issue)
    
    print('Get {0} issues out of {1} issues'.format(len(filtered_issues), len(issues)))
    return filtered_issues

def issues_to_corpus(issues):
    """Convert from list of issues to a corpus.
    An issue will be extracted as its title, description and attachments.
    [title, descriptions, attachments]
    Note: Attachments is also a list of attachments' descriptions
    
    Parameters
    ----------
    issues: List of Issue object
        
    Returns
    -------
    corpus : A dictionary of extracted issues content.
    the key is issue's id and the values are a list of associated contents
    e.g, corpus = {12345:['issue title', 'issue descriptions', 
    ['attachment description 1', attachments description 2']]}
    """    
    corpus = {}
    for issue in issues:
        _id = issue.get_id()
        attachments = ' '.join(item for item in issue.get_attachments())
        content = [item for item in [issue.get_title(), issue.get_description(), attachments] if item != '' and item != None]
        corpus[_id] = content
    
    return corpus

def xml_to_issues(f):
    """Extract issue data from xml file to make an issue list
    
    Parameters
    ----------
    file : string 
        XML file path
    
    Returns
    -------
    issues : list
        issues list
    """
    parser = etree.XMLParser(ns_clean=True, remove_comments=True)
    tree = etree.parse(f, parser)
    root = tree.getroot()
    
    issues = []
    issues_e = root.find('issues') # find all issues
    for issue_e in issues_e:
        attachments = []
        _id = issue_e.find('id').text
        title = issue_e.find('title').text
        description = issue_e.find('description').text
        for item in issue_e.findall('.//attachment'):
            attachments.append(item.text)            
        comments = issue_e.find('comments').text
        commenters = issue_e.find('commenters').text
        issues.append(Issue(_id, title, description, attachments, int(comments), int(commenters)))
        
    return issues

def xml_to_corpus(f):
    """Extract issue data from xml file to make a corpus
    
    Parameters
    ----------
    file : string 
        XML file path
    
    Returns
    -------
    corpus : A dictionary-like
        Collection of extracted issues content.the key is issue's id and the values are a list of associated contents.
        e.g, corpus = {12345:['issue title', 'issue descriptions', 
        ['attachment description 1', attachments description 2']]}
    """
    parser = etree.XMLParser(ns_clean=True, remove_comments=True)
    tree = etree.parse(f, parser)
    root = tree.getroot()
    
    corpus = {}
    issues_e = root.find('issues') # find all issues
    for issue_e in issues_e:
        _id = issue_e.find('id').text
        title = issue_e.find('title').text
        description = issue_e.find('description').text
        attachments = ' '.join(item.text for item in issue_e.findall('.//attachment'))            
        # Combine all non-empty items to the content list
        content = [item for item in [title, description, attachments] if item != '' and item != None]
        corpus[_id] = content
    
    return corpus
        
def print_top_words(model, _id, feature_names, n_top_words):
    """Print topic words from topic modeling models
    
    Parameters
    ----------
    model : a LatentDirichletAllocation or NMF object
        A topic modeling trained model, either using LDA or NMF
    
    feature_names : list
        List of topic words generated from running model
        
    n_top_words : integer
        Number of top words for each topic
        
    Returns
    -------
    None
    """
    print('Topic words for issue %s' % _id)
    for topic_idx, topic in enumerate(model.components_):
        message = "Topic #%d: " % (topic_idx+1)
        message += " ".join([feature_names[i]
                             for i in topic.argsort()[:-n_top_words - 1:-1]])
        print(message)
    print('')

def make_topic_words(model, feature_names, n_top_words):
    """Extract topic words from topic modeling models
    
    Parameters
    ----------
    model : a LatentDirichletAllocation or NMF object
        A topic modeling trained model, either using LDA or NMF
    
    feature_names : list
        List of topic words generated from running model
        
    n_top_words : integer
        Number of top words for each topic
        
    Returns
    -------
    topic_words : list of string
        List of generated topic words for all topics in the model
    """
    topic_words = []
    for topic in model.components_:
        tw = [feature_names[i] for i in topic.argsort()[:-n_top_words-1:-1]]
        u_list = unique_list(tw)
        topic_words.extend(u_list)
    return topic_words
        

def topic_modeling_lda(corpus, n_topics, n_top_words):
    """Extract topics from a corpus using latent direlect allocation
    
    Parameters
    ----------
    corpus : a dictionary-like corpus
        Collection of documents to do topic modeling
    
    n_topics : integer
        Number of topics to be generated54321`
        
    n_top_words : integer
        Number of most important words in the topics
    
    Returns
    -------
    topics : a dictionary-like collection.
        Mapping from issues id (string) to its topic words (list of string)
    """
    # precondition check
    if corpus == None or n_topics <= 0 or n_top_words <= 0:
        return None
    
    topics = {} # mapping from issue id to topic words
    
    for k, v in corpus.items():
        try:
            tf_vectorizer = CountVectorizer(max_df=0.95, min_df=0.5,
                                            max_features=n_features,
                                            stop_words='english')
            tf = tf_vectorizer.fit_transform(v)
            # Fit the LDA model
            lda = LatentDirichletAllocation(n_components=n_topics, max_iter=10,
                                            learning_method='online',
                                            learning_offset=50.,
                                            random_state=0).fit(tf)
            tf_feature_names = tf_vectorizer.get_feature_names()
            print_top_words(lda, k, tf_feature_names, n_top_words)
            # Add list topic words into topics
            topics[k] = make_topic_words(lda, tf_feature_names, n_top_words) 
        except ValueError:
            print('Error in id %s. There are only a few words (%d words) in content so couldn\'t extract topics!' % (k, sum(len(item.split()) for item in v)))
    
    return topics

def topic_modeling_nmf(corpus, n_topics, n_top_words):
    """Extract topics from a corpus using non-negative matrix factorization
    
    Parameters
    ----------
    corpus : a dictionary-like corpus
        Collection of documents to do topic modeling
    
    n_topics : integer
        Number of topics to be generated54321`
        
    n_top_words : integer
        Number of most important words in the topics
    
    Returns
    -------
    topics : a dictionary-like collection.
        Mapping from issues id (string) to its topic words (list of string)
    """
    # precondition check
    if corpus == None or n_topics <= 0 or n_top_words <= 0:
        return None
    
    topics = {} # mapping from issue id to topic words
    
    for k, v in corpus.items():
        try:
            # Use tf-idf features for Non-negative Matrix Factorization (NMF)
            tfidf_vectorizer = TfidfVectorizer(max_df=0.95, min_df=0.2,
                                               max_features=n_features,
                                               stop_words='english')
            tfidf = tfidf_vectorizer.fit_transform(v)
            # Fit the NMF model
            nmf = NMF(n_components=n_topics, random_state=1,
                      beta_loss='kullback-leibler', solver='mu', max_iter=1000, 
                      alpha=.1, l1_ratio=.5).fit(tfidf)
            
            print("\nTopics in NMF model (generalized Kullback-Leibler divergence):")
            tfidf_feature_names = tfidf_vectorizer.get_feature_names()
            print_top_words(nmf, k, tfidf_feature_names, n_top_words)
            # Add list topic words into topics
            topics[k] = make_topic_words(nmf, tfidf_feature_names, n_top_words) 
        except ValueError:
            print('Error in id %s. There are only a few words (%d words) in content so couldn\'t extract topics!' % (k, sum(len(item.split()) for item in v)))
    
    return topics

def load_word_list(wl_type):
    """Load word list from file given word list type
    
    Parameters
    ----------
    wl_type : string
        Type of word list of non-functional requirements category.
            + efficiency
            + functionality
            + usability
            + reliability
            + maintainability
            + portability
    Returns
    -------
    wl : list
        A string list of corresponding word list
    """
   
    filepath = WORD_LIST.get(wl_type.lower())
    if filepath is None:    # non-functional requirement category is not defined in word list
        return None
    
    wordlist = []
    with open(filepath) as f:
        for word in f:
            wordlist.append(word.strip())
    
    return wordlist

def determine_nfr_category(vocabulary):
    """Count number of occurrences of each topic word in each non-functional requirements
    word list and determine the non-functional requirement category.
    
    Parameters
    ----------
    vocabulary : list
        List of the topic words extracted from issues description 
    
    Returns
    -------
    nfr_categories : string
        A string represent for nfr category
    
    Note: if two nfr category has exact same topic words occurrence, this will return the first encounter
    """
    nfr_categories = {}
    for category in WORD_LIST.keys():
        try:
            wl = load_word_list(category)
            cv = CountVectorizer(vocabulary=vocabulary)
            result_array = cv.fit_transform(wl).toarray()
            nfr_categories[category] = np.count_nonzero(result_array == 1)
        except ValueError:
            print('Error: ', vocabulary)
    
    # Find the category with largest words matched
    category = max(nfr_categories, key=lambda key: nfr_categories[key])
    
    # Return None if the requirement is not non-functional
    return category if nfr_categories[category] > 0 else None

def assign_nfr_category(topics):
    """Assign non-functional category for the issues
    
    Parameters
    -----------
    topics : dictionary
        Mapping from issue id to topic words associate with that issue
        
    Returns
    -------
    issue_nfr_category : dictionary-like object
        Mapping from issue to its determined nfr category (None if it's not nfr)
    """
    
    issue_nfr_category ={}
    for issue_id, topic_words in topics.items():
        category = determine_nfr_category(topic_words)
        issue_nfr_category[issue_id] = category
        
        print('Id {:>5} \t\t Category: {:>15}'.format(issue_id, category))
        
    return issue_nfr_category
        
def main():
    issues = filter_issues(xml_to_issues('data/mylyn-enhancement-issues.xml'), commenter_std_dev=3)
    corpus = issues_to_corpus(issues)
    lda_topics = topic_modeling_lda(corpus=corpus, n_topics=1, n_top_words=2)
    # nmf_topics = topic_modeling_nmf(corpus = corpus, n_topics = 2, n_top_words = 5)
    categories = assign_nfr_category(lda_topics)
    
if __name__ == '__main__':
    main()
