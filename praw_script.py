# Import scripts, gets PRAW for the reddit stuff,
# psycopg2 for the PG stuff
import praw
import psycopg2

# Imports my secret variables cause you can't have my passwords
from secret import client_id, client_secret, password, username, user_agent

# Connects to the db I spun up for this training
conn = psycopg2.connect("dbname=will_reddit user=postgres host=athena")

# Sets up the reddit connection
reddit = praw.Reddit(
    client_id=client_id,
    client_secret=client_secret,
    password=password,
    user_agent=user_agent,
    username=username
)


# Begin the comment parsing. The subreddits that it parses through are on my
# front page. It grabs the top 25 posts on my front page.
def start():
    for submission in reddit.front.hot():
        parse_post(submission)
    conn.close()

# This function parses posts. It grabs the data from posts and puts them into
# the db. Fires off the handler for the poster and comments sections as well.


def parse_post(submission):
    # Inserts the submission data into the database
    author = handle_author(submission.author)
    subreddit = handle_subreddit(submission.subreddit)

    # Inserts the submission data into the db
    new_post = conn.cursor()
    new_post.execute("INSERT INTO posts (score, title, shortlink, gilded, submitter, subreddit) VALUES (%s, %s, %s, %s, %s, %s);",
                     (submission.score, submission.title, submission.shortlink, submission.gilded, author, subreddit))

    # Parse comments for a post
    # for comment in submission.comments:

def handle_author(author):
    # Queries my db to see if a redditor already exists. If he does, pulls his
    # data. If they don't, I add them to the db, then return the object
    user_select = conn.cursor()
    user_select.execute("SELECT username FROM redditors;")
    username_list = user_select.fetchall()

    # Are they there?
    if author in username_list:
        # Grabs the user id since the redditor exists in table
        grab_user = conn.cursor()
        grab_user.execute("SELECT user_id FROM redditors WHERE username = %s;", (author))
        user_id = grab_user.fetchone()
        grab_user.close()
        return user_id
    else:
        # Makes a new redditor since they aren't there
        return create_redditor(author)

def create_redditor(author):
    # Grabs a redditor instance
    redditor = reddit.redditor(author.name)

    # Inserts the new redditor into the table
    new_redditor = conn.cursor()
    new_redditor.execute("INSERT INTO redditors (username, comment_karma, link_karma, creation_date) VALUES ( %s, %s, %s, %s);",
                         (author.name, redditor.comment_karma, redditor.link_karma, date_helper(redditor.created)))
    new_redditor.close()

    # Grabs the most recent id to return
    grab_id = conn.cursor()
    grab_id.execute("SELECT currval('redditors_user_id_seq');")
    new_id = grab_id.fetchone()
    grab_id.close()

    return new_id

def handle_subreddit(subreddit):
    # Queries my db to see if a subreddit already exists. If it does, pulls it's
    # data. If it doesn't, I add it to the db, then return the object
    subreddit_select = conn.cursor()
    subreddit_select.execute("SELECT name FROM subreddits;")
    sub_list = subreddit_select.fetchall()

    # Are they there?
    if subreddit in sub_list:
        # Grabs the user id since the redditor exists in table
        grab_sub = conn.cursor()
        grab_sub.execute("SELECT subreddit_id FROM subreddits WHERE name = %s;", (subreddit))
        sub_id = grab_sub.fetchone()
        grab_sub.close()
        return sub_id
    else:
        # Makes a new subreddit since they aren't there
        return create_subreddit(subreddit)

def create_subreddit(subreddit):
    # Inserts the new subreddit into the table
    new_subreddit = conn.cursor()
    new_subreddit.execute("INSERT INTO subreddits (name) VALUES (%s);", [subreddit.name])
    new_subreddit.close()

    # Grabs the most recent id to return
    grab_id = conn.cursor()
    grab_id.execute("SELECT currval('subreddits_subreddit_id_seq');")
    new_id = grab_id.fetchone()
    grab_id.close()

    return new_id

def date_helper(epoch_date):
    date = conn.cursor()
    date.execute("SELECT TIMESTAMP WITH TIME ZONE 'epoch' + %s * INTERVAL '1 second';", [epoch_date])
    converted = date.fetchone()
    date.close()

    return converted

# Fires the start function
start()