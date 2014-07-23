#!/usr/bin/env python

import urllib
import freebase
import logging
import difflib
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from google.appengine.dist import use_library
use_library('django', '1.2')

from google.appengine.api import users
from google.appengine.ext import blobstore,db,webapp
from google.appengine.ext.webapp import blobstore_handlers,util
from datetime import datetime
#from jinja2 import Template
#from google.appengine.dist import use_library
#use_library('django', '1.2')
#from django import template
from django.template.loader import render_to_string
from django.conf import settings


try:
    import json
except ImportError:
    from django.utils import simplejson as json

#artist url clash resolved by appending genre...?
#song, artist, and album should all be lowercased in order to check for match
#but shouldn't be sent in as lowercase to database...

class Lyrics(db.Model):
    text = db.TextProperty()
    date = db.DateTimeProperty()
    votes = db.IntegerProperty()
    artist = db.StringProperty()
    title = db.StringProperty()

#currently album and artist just string property because they aren't needed
#as anything more than strings here and can be fetched by name when they are
class Song(db.Model):
    songTitle = db.StringProperty()
#    lyrics = db.ReferenceProperty(Lyrics)
    artist = db.StringProperty()
    album = db.StringProperty()
      
class Album(db.Model):
    albumTitle = db.StringProperty()
    
    @property
    def tracks(self):
        tracklisting = AlbumTrack.all().filter('album =',self)
        return tracklisting.fetch(1000)

#unsure if this class makes any sense but here it is anyhow
class AlbumTrack(db.Model):
    album = db.StringProperty()
    track = db.StringProperty()
    

class BaseHandler(webapp.RequestHandler):
    def render_template(self,templateFilename,templateVars,postLoginURL=None):
        if postLoginURL is None:
            postLoginURL = self.request.uri
        newVars = dict(templateVars)
        newVars['user'] = users.get_current_user()
        newVars['current_user_admin'] = users.is_current_user_admin()
        if newVars.get('user'): 
            newVars['logoutURL'] = users.create_logout_url(postLoginURL)
        else:
            newVars['loginURL'] = users.create_login_url(postLoginURL)
        self.response.out.write(render_to_string(templateFilename,newVars))
        
class MainHandler(BaseHandler):
    def get(self):
        allSongs = Song.all().fetch(15)
        title = "Crowdlyrics"
        self.render_template('index.html', {'songlist': allSongs, 'pageTitle': title })
        
class NewHandler(BaseHandler):
    def get(self, artistName, albumTitle):
        albumTitle = str(urllib.unquote(albumTitle))
        artistName = str(urllib.unquote(artistName))
        pageTitle = "Crowdlyrics - add song"
        self.render_template('newsong.html', {'album' : albumTitle, 'artist' : artistName, 'pageTitle' : pageTitle})
        
        
class EditHandler(BaseHandler):
    def get(self, intID):
        intID = int(intID)
        currLyrics = Lyrics.get_by_id(intID)
        pageTitle = "Crowdlyrics - Edit" + currLyrics.title
        self.render_template('edit.html', {'lyrics' : currLyrics, 'pageTitle' : pageTitle })
        
class SongHandler(BaseHandler):
    def get(self, artistName, songTitle):
        songTitle = str(urllib.unquote(songTitle))
        artistName = str(urllib.unquote(artistName))
        allSongs = Song.all()
        thisSong = allSongs.filter('songTitle =', songTitle)
        songData = thisSong.fetch(1)
        lyrics = Lyrics.all().filter('title =', songTitle).filter('artist =', artistName).order('-date').fetch(1000)
        if songData:
            album = songData[0].album
        else:
            album = ""
#        logging.info("song data is:" + str(songData))
        pageTitle = "Crowdlyrics - " + songTitle
        self.render_template('song.html', {'lyrics': lyrics, 'album': album, 'title': songTitle, 'artist' : artistName, "pageTitle" : pageTitle })
        
class ArtistHandler(BaseHandler):
    def get(self, artistName):
        name = str(urllib.unquote(artistName))
        query = {
  "name" : name, "type" : "/music/artist", 'album': [{ 'name': None,
                      'release_date': None,
                      'sort': '-release_date' }]
}

        results = freebase.mqlread(query)
        for album in results.album:
            if album.release_date == "(None)":
                album.release_date == ""
        #to be switched to search instead of mqlread...
        pageTitle = "Crowdlyrics - " + name
        self.render_template('artist.html', {'artist': name, 'discography': results.album, 'pageTitle' : pageTitle })
        
        
class AlbumHandler(BaseHandler):
    def get(self, artist, albumName):
        name = str(urllib.unquote(albumName))
        artist = str(urllib.unquote(artist))
        logging.info(name)
        logging.info("work, dammit")
        allSongs = Song.all()
        albumSongs = allSongs.filter('album =', name).fetch(1000)
        pageTitle = "Crowdlyrics - " + name
        self.render_template('album.html', {'album': name, 'artist': artist, 'tracks': albumSongs, 'pageTitle' : pageTitle })

class SearchHandler(BaseHandler):
    def get(self):
        typ = self.request.get('type')
        query = self.request.get('q')
        data = []
        # fetch right data
        # put into python dictionary
        if typ == 'Artist':
            query = [{ "name" : query, "type" : "/music/artist"}]
            results = freebase.mqlread(query)
            logging.info(str(results))
            data = [ i.name for i in results ]
#            data = [query]
        elif typ == 'Album':
            query = [{ "name" : None, "type" : "/music/artist", 'album': query }]
            results = freebase.mqlread(query)
            logging.info(str(results))
            #artist = results.name
            data = [ i.name for i in results ]
            dataList = (list(data))
#            data = [query, results]
            logging.info(dataList)
        else:
            songs = Song.all().fetch(1000)
#            for song in songs:
#                artist = song.artist
#                name = song.songTitle
            names = [ i.songTitle for i in songs ]
            artists = list()
            titles = list()
            matches = difflib.get_close_matches(query, names)
            for song in songs:
                name = song.songTitle
                if name in matches:
                    titles.append(name)
                    artists.append(song.artist)
            data = [artists, titles]
#            songs = map(str, songs)
#            data = [query, songs]
        self.response.out.write(json.dumps(data))
        
class DiffHandler(BaseHandler):
    def get(self):
        firstID = int(self.request.get('q1'))
        secondID = int(self.request.get('q2'))
        c1 = Lyrics.get_by_id(firstID)
        c1text = c1.text
        c2 = Lyrics.get_by_id(secondID)
        c2text = c2.text
        split1 = c1text.splitlines()
        split2 = c2text.splitlines()
        difference = difflib.ndiff(split1, split2)
        crazy = '\n'.join(difference).splitlines()
        modified = list()
#        previous = "-"
        for line in crazy:
            if line:
                if line[0] == "+":
                    line = "<span class='newer '>"+line[1:]+"</span>"
                    modified.append(line)
                elif line[0] == "-" :
                    line = "<span class='older'>"+line[1:]+"</span>"
                    modified.append(line)
                elif line[0] == "?":
                    line = ""
                else:
                    modified.append(line)
        final = '\n'.join(modified)
        self.response.out.write(json.dumps(final))
                

class LyricsHandler(webapp.RequestHandler):
    def post(self):
        newLyrics = Lyrics()
        title = self.request.get('title')
        artist = self.request.get('artist')
        lyricslist = self.request.get('lyrics').splitlines()
        text = '\n'.join(lyricslist)
        newLyrics.text = text
        newLyrics.artist = artist
        newLyrics.title = title
        newLyrics.date = datetime.now()
        newLyrics.votes = 0
        newLyrics.put()
        allSongs = Song.all()
        thisSong = allSongs.filter('songTitle =', title).filter('artist =', artist)
        lyrics = Lyrics.all().filter('title =', title).filter('artist =', artist).order('-date').fetch(1000)
        songData = thisSong.fetch(1)[0]
        pageTitle = "Crowdlyrics - " + title
        self.response.out.write(render_to_string('song.html', {'lyrics': lyrics, 'album': songData.album, 'title': title, 'artist': artist, 'pageTitle': pageTitle}))
        

#deals with creating new song on song page        
class SubmitHandler(webapp.RequestHandler):
    def post(self):
        albumName = self.request.get('album')
        title = self.request.get('title')
        artist = self.request.get('artist')
        thisAlbumTrack = AlbumTrack.all().filter('album =', albumName).filter('track =', title).fetch(1000)
        logging.info("album tracks: %d" % len(thisAlbumTrack))
        if len(thisAlbumTrack) == 0:
            newAlbumTrack = AlbumTrack()
            newAlbumTrack.album = albumName
            newAlbumTrack.track = title
            newAlbumTrack.put()
            newLyrics = Lyrics()
            lyricslist = self.request.get('lyrics').splitlines()
            logging.info ('\n'.join(lyricslist))
            newLyrics.text = '\n'.join(lyricslist)
            newLyrics.date = datetime.now()
            newLyrics.artist = artist
            newLyrics.title = title
            newLyrics.votes = 0
            newLyrics.put()
            newSong = Song() 
            newSong.artist = artist
            newSong.songTitle = title
            newSong.lyrics = newLyrics
            newSong.album = albumName
            newSong.put()
        allSongs = Song.all()
        thisSong = allSongs.filter('songTitle =', title).filter('artist =', artist)
        lyrics = Lyrics.all().filter('title =', title).filter('artist =', artist).order('-date').fetch(1000)
        songData = thisSong.fetch(1)
        pageTitle = "Crowdlyrics - " + title
        self.response.out.write(render_to_string('song.html', {'lyrics': lyrics, 'album': albumName, 'title': title, 'artist': artist, 'pageTitle': pageTitle}))
  
   
   
def main():
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
    application = webapp.WSGIApplication([('/', MainHandler),
                                          ('/newsong/([^/]+)?/([^/]+)?', NewHandler),
                                          (r'/song/([^/]+)?/([^/]+)?', SongHandler),
                                          (r'/artist/([^/]+)?', ArtistHandler),
                                          (r'/album/([^/]+)?/([^/]+)?', AlbumHandler),
                                          ('/submit', SubmitHandler),
                                          ('/search', SearchHandler),
                                          ('/lyrics', LyricsHandler),
                                          ('/diff', DiffHandler),
                                          ('/edit/([\b\d+\b]+)?', EditHandler) ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()