# Import scripts, gets PRAW for the reddit stuff,
# psycopg2 for the PG stuff
import praw
import psycopg2
import sys
import subprocess
import threading

# Imports my secret variables cause you can't have my passwords
from secret import client_id, client_secret, password, username, user_agent

# DB connection thingy
path_db_info_script = '/praw/reddit-training/get_db_info.pl'

# Connects to the db I spun up for this training. Thanks Harrison!
host = 'athena'
port = '5432'
name = 'will_reddit'
user = 'postgres'

if(not host):
    s_fatal("Failed to retrieve db hostname!")
    sys.exit(-1)

if(not port):
    s_fatal("Failed to retrieve db port!")
    sys.exit(-1)

if(not name):
    s_fatal("Failed to retrieve db name!")
    sys.exit(-1)

if(not user):
    s_fatal("Failed to retrieve db user!")
    sys.exit(-1)

host = host.rstrip()
port = port.rstrip()
name = name.rstrip()
user = user.rstrip()

# Sets up the reddit connection
reddit = praw.Reddit(
    client_id=client_id,
    client_secret=client_secret,
    password=password,
    user_agent=user_agent,
    username=username
)

conn = psycopg2.connect(
    host=host,
    port=port,
    database=name,
    user=user
)

# Sets up the lock so that pg connections don't get terminated by each other
parse_post_lock       = threading.RLock()
handle_author_lock    = threading.RLock()
create_redditor_lock  = threading.RLock()
handle_subreddit_lock = threading.RLock()
create_subreddit_lock = threading.RLock()
date_helper_lock      = threading.RLock()

threadLocal = threading.local()

threads = []

# Begin the comment parsing. The subreddits that it parses through are on my
# front page. It grabs the top 25 posts on my front page.
def start():
    thread_handler(reddit.front.hot(), 'hot front page')
    thread_handler(reddit.subreddit('all').hot(), 'hot /r/all')
    thread_handler(reddit.front.rising(), 'rising front page')
    thread_handler(reddit.subreddit('all').rising(), 'rising /r/all')

    # Closes the connection after all threads finish
    for x in threads:
        x.join()


def thread_handler(submissions, type_string):
    # Creates my thread
    t = threading.Thread(target=subreddit_parse, args=(submissions, type_string))

    # Starts the thread
    t.start()
    print("Starting: " + type_string)

    # Connections are thread safe I think
    print("Connecting with database information (%s): host=%s, port=%s, name=%s, user=%s" % (
        type_string, host, port, name, user))


    # Appends it for later joining
    threads.append(t)

def subreddit_parse(submissions, type_string):
    post_num = 1
    for submission in submissions:
        print("Parsing " + type_string + " post #" + str(post_num))
        parse_post(submission)
        post_num = post_num+1


# This function parses posts. It grabs the data from posts and puts them into
# the db. Fires off the handler for the poster and comments sections as well.
def parse_post(submission):
    # Inserts the submission data into the database. This grabs 100 posts, updates a tracker as a result
    author = handle_author(submission.author)
    subreddit = handle_subreddit(submission.subreddit)

    # Inserts the submission data into the db
    parse_post_lock.acquire()

    new_post = conn.cursor()
    try:
        new_post.execute("INSERT INTO posts (score, title, shortlink, gilded, submitter, subreddit) VALUES (%s, %s, %s, %s, %s, %s);",
                         (submission.score, submission.title, submission.shortlink, submission.gilded, author, subreddit))
        conn.commit()
    except:
        print("DB insertion error, probably a duplicate value, fairly common. Rolls back the error")
        conn.rollback()

    new_post.close()
    parse_post_lock.release()

# Queries my db to see if a redditor already exists. If he does, pulls his
# data. If they don't, I add them to the db, then return the object
def handle_author(author):
    handle_author_lock.acquire()

    user_select = conn.cursor()
    user_select.execute("SELECT username FROM redditors;", ())
    username_list = user_select.fetchall()
    user_select.close()

    # Are they there?
    if author in username_list:
        # Grabs the user id since the redditor exists in table
        grab_user = conn.cursor()
        grab_user.execute("SELECT user_id FROM redditors WHERE username = %s;", (author))
        user_id = grab_user.fetchone()
        grab_user.close()

        handle_author_lock.release()
        return user_id[0]
    else:
        # Makes a new redditor since they aren't there
        handle_author_lock.release()
        return create_redditor(author)

def create_redditor(author):
    create_redditor_lock.acquire()

    # Grabs a redditor instance
    redditor = reddit.redditor(author.name)

    # Inserts the new redditor into the table. I added try catch because of 404's
    new_redditor = conn.cursor()
    try:
        new_redditor.execute("INSERT INTO redditors (username, comment_karma, link_karma, creation_date) VALUES ( %s, %s, %s, %s);",
                             (author.name, redditor.comment_karma, redditor.link_karma, date_helper(redditor.created)))
    except:
        print("I just caught a 404. Fix ur servers Mr. Reddit")

    new_redditor.close()

    # Grabs the most recent id to return
    grab_id = conn.cursor()
    grab_id.execute("SELECT currval('redditors_user_id_seq');")
    new_id = grab_id.fetchone()
    grab_id.close()

    create_redditor_lock.release()
    return new_id[0]

def handle_subreddit(subreddit):
    handle_subreddit_lock.acquire()

    # Queries my db to see if a subreddit already exists. If it does, pulls it's
    # data. If it doesn't, I add it to the db, then return the object
    subreddit_select = conn.cursor()
    subreddit_select.execute("SELECT name FROM subreddits;")
    sub_list = subreddit_select.fetchall()
    subreddit_select.close()

    # Are they there?
    if subreddit in sub_list:
        # Grabs the user id since the redditor exists in table
        grab_sub = conn.cursor()
        grab_sub.execute("SELECT subreddit_id FROM subreddits WHERE name = %s;", (subreddit))
        sub_id = grab_sub.fetchone()
        grab_sub.close()

        handle_subreddit_lock.release()
        return sub_id[0]
    else:
        # Makes a new subreddit since they aren't there
        handle_subreddit_lock.release()
        return create_subreddit(subreddit)

# Creates new subreddits to be cataloged
def create_subreddit(subreddit):
    create_subreddit_lock.acquire()

    # Inserts the new subreddit into the table
    new_subreddit = conn.cursor()
    new_subreddit.execute("INSERT INTO subreddits (name) VALUES (%s);", [subreddit.display_name])
    new_subreddit.close()

    # Grabs the most recent id to return
    grab_id = conn.cursor()
    grab_id.execute("SELECT currval('subreddits_subreddit_id_seq');")
    new_id = grab_id.fetchone()
    grab_id.close()

    create_subreddit_lock.release()
    return new_id[0]

# Converts the reddit epoch timestamps into a PG friendly timestamp
def date_helper(epoch_date):
    date_helper_lock.acquire()

    date = conn.cursor()
    date.execute("SELECT TIMESTAMP WITH TIME ZONE 'epoch' + %s * INTERVAL '1 second';", [epoch_date])
    converted = date.fetchone()
    date.close()

    date_helper_lock.release()
    return converted[0]

# Fires the start function
start()
