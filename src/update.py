#!/usr/bin/python

import feedparser
import time
import urllib.request
import configparser
import boto3


class RSS2Pocket:

    config = None
    send_to_pocket_flag = True

    def send_to_pocket(self, name, url_feed, fake):

        import urllib.request
        import urllib.parse

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

        #
        # Don't do anything if in fake mode
        #

        if not self.send_to_pocket_flag:
            print("Not really sending to pocket, fake mode active")
            return True

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

    def process_feeds(self, table, name, url, fake=False):
        #
        # function to get the current time
        #
        current_time_millis = lambda: int(round(time.time() * 1000))
        current_timestamp = current_time_millis()

        def post_is_in_db(_table, _name, _title):
            response = _table.get_item(
                Key={
                    'name': _name,
                    'title': _title
                }
            )
            #print(response)
            if "Item" in response:
                return True
            else:
                return False

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

            try:
                # title = post.title
                title = post.link

                #if "published" in post:
                #    print(post.published)
                #else:
                #    print("Unknown")

                if self.config["Pocket"]["fake_run"] == "yes":
                    print(post)
                    pass
                else:
                    if post_is_in_db(table, name, title):
                        posts_to_skip.append(title)
                    else:
                        posts_to_print.append(title)
            except Exception:
                print("Exception reading post data")
                print(post)

        #
        # add all the posts we're going to print to the database with the current timestamp
        # (but only if they're not already in there)
        #
        for title in posts_to_print:
            if not post_is_in_db(table, name, title):
                if self.send_to_pocket(name, title, fake):
                    print("Sent to pocket: " + title)

                    # Insert into dynamodb!
                    table.put_item(
                        Item={
                            'name': name,
                            'title': title,
                            'ts': current_timestamp
                        }
                    )
                else:
                    print("Could not send to Pocket")

    def main(self):
        self.config = configparser.ConfigParser()
        files = self.config.read("config.ini")
        if len(files) == 0:
            print("Could not read config file")
            exit(1)

        import os
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
        dynamodb = boto3.resource(
            'dynamodb',
            aws_access_key_id=self.config["Pocket"]["aws_key"],
            aws_secret_access_key=self.config["Pocket"]["aws_secret"]
        )

        table = dynamodb.Table('feeds')
        #print(table.creation_date_time)

        limit = 1000 * 60 * 0 # 12 * 3600 * 1000

        feeds = []
        try:
            feeds = open("feeds.txt", mode="r")
        except:
            print("Cannot read feeds.txt file")
            exit(0)

        for line in feeds:
            line = line.rstrip()
            if line and line != "":
                #print("======" + line + "========")
                label, url = line.split(",")
                label = label.strip()
                url = url.strip()
                if label[0] != "#":
                    self.process_feeds(table, label, url)

        #rows = c.execute('select * from feeds')
        #for row in rows:
        #    print(row)


if __name__ == "__main__":

    main = RSS2Pocket()
    main.main()

