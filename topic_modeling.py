# Topic modeling with scikit-learn
# Some methods are inspired from scikit-learn tutorials
# topic_modeling.py

from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import NMF, LatentDirichletAllocation

from scraper import multiprocess_scrape, split_range

n_features = 1000
# n_components = 10
n_top_words = 10

def to_corpus(issues):
    """Convert from list of issues to a corpus.
    An issue will be extracted as its title, description and attachments.
    [title, descriptions, attachments]
    Note: Attachments is also a list of attachments' descriptions
    -----------------------
    Arguments:
        issues: List of Issue object
        
    Returns:
        corpus: A dictionary of extracted issues content.
                the key is issue's id and the values are a list of associated contents
                e.g, corpus = {12345:['issue title', 'issue descriptions', 
                                    ['attachment description 1', attachments description 2']]}
    """    
    corpus = {}
    for issue in issues:
        _id = issue.get_id()
        content = [issue.get_title(), issue.get_description()]
        attachments = ' '.join(item for item in issue.get_attachments())
        if attachments != '':
            content.append(attachments)
        else:
            print('Attachments are empty!')
        corpus[_id] = content
    
    return corpus

def print_top_words(model, feature_names, n_top_words):
    for topic_idx, topic in enumerate(model.components_):
        message = "Topic #%d: " % topic_idx
        message += " ".join([feature_names[i]
                             for i in topic.argsort()[:-n_top_words - 1:-1]])
        print(message)
    print()

def topic_modeling(corpus, num_topics):
    """Extract topics from a corpus
    
    Parameters:
        corpus: a dictionary-like corpus which maps
    """
    # precondition check
    if corpus == None:
        return None
    
    topics = {} # mapping from issue id to topic words
    
    for k, v in corpus.items():
        # Use tf-idf features for Non-negative Matrix Factorization (NMF)
        tfidf_vectorizer = TfidfVectorizer(max_df=0.95, min_df=0.2,
                                           max_features=n_features,
                                           stop_words='english')
        
        tfidf = tfidf_vectorizer.fit_transform(v)
        
        # Use tf (raw term count) features for LDA
        tf_vectorizer = CountVectorizer(max_df=0.95, min_df=0.2,
                                       max_features=n_features,
                                       stop_words='english')
        
        tf = tf_vectorizer.fit_transform(v)
        
        # Fit the NMF model
        nmf = NMF(n_components=num_topics, random_state=1,
                  beta_loss='kullback-leibler', solver='mu', max_iter=1000, 
                  alpha=.1, l1_ratio=.5).fit(tfidf)
        
        print("\nTopics in NMF model (generalized Kullback-Leibler divergence):")
        tfidf_feature_names = tfidf_vectorizer.get_feature_names()
        print_top_words(nmf, tfidf_feature_names, n_top_words)
        
        # Fit the LDA model
        lda = LatentDirichletAllocation(n_components=num_topics, max_iter=5,
                                        learning_method='online',
                                        learning_offset=50.,
                                        random_state=0).fit(tf)
        tf_feature_names = tf_vectorizer.get_feature_names()
        print_top_words(lda, tf_feature_names, n_top_words)    
    
def main():
    ids = split_range([300000, 300100], 5)
    issues = multiprocess_scrape('Mylyn', ids, 5)
    corpus = to_corpus(issues)
    topic_modeling(corpus, 10)

if __name__ == '__main__':
    main()
# print(corpus)