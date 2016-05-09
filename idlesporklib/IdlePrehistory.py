import pickle
import os
import threading

NSESSIONS_TO_SAVE = 30
MAX_LEN = 10000
UPDATE_EVERY = 60*5

def concat_lists(lists):
    C = []
    for l in lists:
        C.extend(l)
    return C


class Prehistory(object):
    def __init__(self, path):
        self.PATH = path + '/.idlesporkhistory.pickle'
        self.history = {}
        self.sessid = 0
        self.noprehist = False
        if not os.path.exists(self.PATH):
            # create an empty file
            self.dump_file({})
        else:
            try:
                self.history = self.load_file()
                self.sessid = max(self.history.keys())+1
            except Exception:
                print
                print 'Unable to load prehistory.'
                print 'Removing your prehistory file will probably fix it.'
                print 'You can do it by running: rm "%s"' % self.PATH
                self.noprehist = True
        if (len(self.history) > NSESSIONS_TO_SAVE) and (sum([len(x) for x in self.history.values()]) > MAX_LEN):
            del self.history[min(self.history.keys())]
        self.history[self.sessid] = []
        self.STOPUPDATE=False
        self.timer = self.autoupdate()
    
    def load_file(self):
        fl = open(self.PATH, 'rb')
        hist = pickle.load(fl)
        fl.close()
        return hist

    # VERY safe dump file. Will be very weird if files become corrupt now. 
    def dump_file(self, content):
        counter = 0
        while True:
            while True:
                try:
                    fl = open(self.PATH+'.tmp', 'wb')
                    pickle.dump(content, fl)
                    fl.close()
                    fl = open(self.PATH+'.tmp','rb')
                    h2 = pickle.load(fl)
                    fl.close()
                    assert h2 == content
                    break
                except:
                    #print '\nThere was an error dumping the history!\n'\
                    #'This happened %d times so far, trying again...'%(counter)
                    counter+=1
            try:
                if os.path.exists(self.PATH):
                    os.remove(self.PATH)
                os.rename(self.PATH+'.tmp',self.PATH)
                fl = open(self.PATH,'rb')
                h2 = pickle.load(fl)
                fl.close()
                assert h2 == content
                break
            except:
                pass
		#print '\nThere was an error MOVING the history! WEIRD!\n'\
                #'Trying again, but please tell the devs about this.'
                    
    def get(self):
        return concat_lists(self.history.values())

    def append(self,other):
        self.history[self.sessid].append(other)
    
    def remove(self,other):
        self.history[self.sessid].remove(other)

    def update(self):
        if self.noprehist: return
        try:
            currhist = self.load_file()
            currhist[self.sessid] = self.history[self.sessid]
            self.dump_file(currhist)
        except Exception, e:
            print e
            return

    def autoupdate(self):
        self.update()
        if not self.STOPUPDATE:
            self.timer = threading.Timer(UPDATE_EVERY, self.autoupdate)
            self.timer.start()
            return self.timer
    
    def __del__(self):
        self.update()
        self.STOPUPDATE = True
        self.timer.cancel()
