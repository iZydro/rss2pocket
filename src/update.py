#!/usr/bin/python

import feedparser
import time
import sqlite3
import urllib.request
import configparser


class RSS2Pocket:

    config = None
    send_to_pocket_flag = True

    def send_to_pocket(self, name, url_feed, fake):

        import urllib.request
        import urllib.parse

        #
        # Don't do anything if in fake mode
        #

        if not self.send_to_pocket_flag:
            print("Not really sending to pocket, fake mode active")
            return True

        try:
            consumer_key = self.config["Pocket"]["consumer_key"]
            access_token = self.config["Pocket"]["access_token"]
        except:
            print("Cannot read Pocket data from config.ini")
            return False

        try:
            self.send_to_pocket_flag = self.config["Pocket"]["send_to_pocket"].lower() != "no"
        except:
            pass

        METHOD_URL = 'https://getpocket.com/v3/'
        REQUEST_HEADERS = { 'X-Accept': 'application/json' }

        params = {
            'tags'         : name + ',' + 'pypocket',
            'url'          : url_feed
        }

        params["consumer_key"] = consumer_key
        params["access_token"] = access_token

        encoded = urllib.parse.urlencode(params).encode('utf-8')

        request = urllib.request.Request(METHOD_URL + "add", encoded, REQUEST_HEADERS)

        try:
            resp = urllib.request.urlopen(request)
            print(resp.read())
        except Exception as e:
            print(e)
            return False

        return True

    def process_feeds(self, c, conn, name, url, fake=False):
        #
        # function to get the current time
        #
        current_time_millis = lambda: int(round(time.time() * 1000))
        current_timestamp = current_time_millis()

        def post_is_in_db(c, conn, title):
            rows = c.execute('select * from feeds where url=?', (title,))
            return rows.fetchone() != None

        # return true if the title is in the database with a timestamp > limit
        def post_is_in_db_with_old_timestamp(c, conn, title):
            rows = c.execute('select * from feeds where url=? and timestamp<?', (title, current_timestamp))
            return rows.fetchone() != None

        print("Processing: " + url)

        #
        # get the feed data from the url
        #


        '''
        feed_request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla'})

        try:
            feed_resp = urllib.request.urlopen(feed_request)
            line = feed_resp.readline().decode('utf-8')
            feed_read = ""
            while line:
                if line != '\n' and line != '\r\n':
                    feed_read += str(line)
                else:
                    pass
                line = feed_resp.readline().decode('utf-8')
        except Exception as e:
            print(e)
            return False

        feed = feedparser.parse(feed_read)
        '''

        feed = feedparser.parse(url)

        #
        # figure out which posts to print
        #
        posts_to_print = []
        posts_to_skip = []

        for post in feed.entries:
            # if post is already in the database, skip it
            # TODO check the time
            title = post.title
            title = post.link
            if post_is_in_db_with_old_timestamp(c, conn, title):
                posts_to_skip.append(title)
            else:
                posts_to_print.append(title)

        #
        # add all the posts we're going to print to the database with the current timestamp
        # (but only if they're not already in there)
        #
        for title in posts_to_print:
            if not post_is_in_db(c, conn, title):
                if self.send_to_pocket(name, title, fake):
                    print("Sent to pocket: " + title)
                    c.execute('insert into feeds values(?, ?, ?)', (name, title, current_timestamp))
                    conn.commit()
                else:
                    print("Could not send to Pocket")

    def main(self):
        self.config = configparser.ConfigParser()
        files = self.config.read("config.ini")
        if len(files) == 0:
            print("Could not read config file")
            exit(1)

        conn = sqlite3.connect('example.db')
        c = conn.cursor()
        c.execute('create table if not exists feeds (id string, url string, timestamp real) ')
        conn.commit()

        limit = 1000 * 60 * 0 # 12 * 3600 * 1000

        feeds = []
        try:
            feeds = open("feeds.txt", mode="r")
        except:
            print("Cannot read feeds.txt file")
            exit(0)

        for line in feeds:
            label, url = line.split(",")
            label = label.strip()
            url = url.strip()
            if label[0] != "#":
                self.process_feeds(c, conn, label, url)

        #rows = c.execute('select * from feeds')
        #for row in rows:
        #    print(row)

if __name__ == "__main__":

    main = RSS2Pocket()
    main.main()

