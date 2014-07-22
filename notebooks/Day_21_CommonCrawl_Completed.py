# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=1>

# Goals

# <markdowncell>

# For us to learn:
# 
# * the basics of how to process CommonCrawl data by counting files and tallying file sizes in the CC crawl
# * **how to do this processing in parallel fashion using PiCloud, Amazon AWS (specifically S3), the [`boto` library](http://boto.readthedocs.org/en/latest/)** 
# 
# This notebook duplicates some of [Day_20_CommonCrawl_Starter](http://nbviewer.ipython.org/urls/raw.github.com/rdhyee/working-open-data/master/notebooks/Day_20_CommonCrawl_Starter.ipynb).
# 
# For moving files between your computer and PiCloud, look at [Day_20_Moving_files_to_PiCloud.ipynb](http://nbviewer.ipython.org/urls/raw.github.com/rdhyee/working-open-data/master/notebooks/Day_20_Moving_files_to_PiCloud.ipynb).
# 
# For understanding the actual content of the files in Common Crawl, we'll look at [Day_21_CommonCrawl_Content.ipynb](http://nbviewer.ipython.org/urls/raw.github.com/rdhyee/working-open-data/master/notebooks/Day_21_CommonCrawl_Content.ipynb)

# <headingcell level=1>

# Learning about Common Crawl structure

# <markdowncell>

# Good to review Dave Lester's talk: http://www.slideshare.net/davelester/introduction-to-common-crawl  
# 
# If you need general intro to Common Crawl, watch the [Common Crawl Video](https://www.youtube.com/watch?v=ozX4GvUWDm4).

# <headingcell level=2>

# Common Crawl data stored in Amazon S3

# <markdowncell>

# The Common Crawl data structure is documented at https://commoncrawl.atlassian.net/wiki/display/CRWL/About+the+Data+Set. To quote the docs:
# 
# The entire Common Crawl data set is stored on Amazon S3 as a Public Data Set:
# 
#     http://aws.amazon.com/datasets/41740
# 
# The data set is divided into three major subsets:
# 
# * Archived Crawl #1 - s3://aws-publicdatasets/common-crawl/crawl-001/ - crawl data from 2008/2010
# * Archived Crawl #2 - s3://aws-publicdatasets/common-crawl/crawl-002/ - crawl data from 2009/2010
# * Current Crawl - s3://aws-publicdatasets/common-crawl/parse-output/ - crawl data from 2012
# 
# The two archived crawl data sets are stored in folders organized by the year, month, date, and hour the content was crawled.  For example:
# 
#     s3://aws-publicdatasets/common-crawl/crawl-002/2010/01/06/10/1262847572760_10.arc.gz
# 
# The current crawl data set is stored in the "parse-output" folder in a similar manner to how Nutch stores archives.  Crawl data is stored in a "segments" subfolder, then in a folder that starts with the UNIX timestamp of crawl start time.  For example:
# 
#     s3://aws-publicdatasets/common-crawl/parse-output/segment/1341690169105/1341826131693_45.arc.gz

# <headingcell level=2>

# Using s3cmd and boto to confirm the examples from the documentation

# <codecell>

# s3cmd installed in custom PiCloud environment -- and maybe in your local environment too

# confirm s3://aws-publicdatasets/common-crawl/crawl-002/2010/01/06/10/1262847572760_10.arc.gz
# doc for s3cmd: http://s3tools.org/s3cmd

!s3cmd ls s3://aws-publicdatasets/common-crawl/crawl-002/2010/01/06/10/1262847572760_10.arc.gz

# <headingcell level=3>

# EXERCISE:  use s3cmd to confirm existence of `s3://aws-publicdatasets/common-crawl/parse-output/segment/1341690169105/1341826131693_45.arc.gz`

# <codecell>

!s3cmd ls s3://aws-publicdatasets/common-crawl/parse-output/segment/1341690169105/1341826131693_45.arc.gz

# <headingcell level=2>

# using s3cmd to look at parse-output and valid_segments.txt in current crawl

# <codecell>

# looking at parse-output itself

!s3cmd ls s3://aws-publicdatasets/common-crawl/parse-output

# <codecell>

# looking at what is contained by parse-output "folder"

!s3cmd ls s3://aws-publicdatasets/common-crawl/parse-output/

# <markdowncell>

# There is a list of "valid segments" in 
# 
#     s3://aws-publicdatasets/common-crawl/parse-output/valid_segments.txt
# 
# -- a list of segments that are part of the current crawl.  Let's download it and study it.
# 
# See [discussion about valid segments](https://groups.google.com/forum/#!msg/common-crawl/QYTmnttZZyo/NPiXvK8ZeiMJ)

# <codecell>

!s3cmd ls s3://aws-publicdatasets/common-crawl/parse-output/valid_segments.txt

# <codecell>

# we can download it:

!s3cmd get --force s3://aws-publicdatasets/common-crawl/parse-output/valid_segments.txt

# <codecell>

!head valid_segments.txt

# <headingcell level=2>

# using boto to study parse-output and valid_segments.txt

# <codecell>

# http://boto.s3.amazonaws.com/s3_tut.html

import boto
from boto.s3.connection import S3Connection

from itertools import islice

conn = S3Connection()

# turns out there is an anonymous mode in boto for public data sets:
# https://github.com/keiw/common_crawl_index/commit/ad341d0a41a828f260c9c08419dadff0dac6cf5b#L0R33
#conn=S3Connection(anon=True)

bucket = conn.get_bucket('aws-publicdatasets')
for key in islice(bucket.list(prefix="common-crawl/parse-output/", delimiter="/"),None):
    print key.name.encode('utf-8')

# <codecell>

# get valid_segments
# https://commoncrawl.atlassian.net/wiki/display/CRWL/About+the+Data+Set

import boto
from boto.s3.connection import S3Connection

conn = S3Connection()
bucket = conn.get_bucket('aws-publicdatasets')

k = bucket.get_key("common-crawl/parse-output/valid_segments.txt")
s = k.get_contents_as_string()

valid_segments = filter(None, s.split("\n"))

print len(valid_segments), valid_segments[0]

# <codecell>

# valid_segments are Unix timestamps (in ms) -- confirm current crawl is from 2012

import datetime
datetime.datetime.fromtimestamp(float(valid_segments[0])/1000.)

# <headingcell level=1>

# Using boto to compile stats on each valid segment

# <markdowncell>

# As of the time of this writing (April 4, 2013), there are 177 valid segments in the current crawl.  Now, it's time to figure out how to write a Python function called `segment_stats` that takes a segment id and an optional `stop` parameter (for the max number of keys to iterate through) of the form
# 
#     def segment_stats(seg_id, stop=None):
#         pass
#         # YOUR EXERCISE TO FILL IN
# 
# and returns a `dict` with 2 keys:  
# 
# * `count` holding the number of keys inside the given valid segment
# * `size` holding the total number of bytes held in the keys
# 
# broken down by file type (there are 3 major types):
# 
# * `arg.gz` for the 
# * 'metadata' for the metadata files
# * 'textData' for the textdata files
# * 'success' for success files
# 
# For example:
# 
#     segment_stats('1346823845675', None)
# 
# should return:
# 
#     {
#      'count': {'arc.gz': 11904, 'metadata': 4377, 'success': 1, 'textData': 4377},
#      'size': {'arc.gz': 967409519222,
#           'metadata': 187079951008,
#           'success': 0,
#           'textData': 129994977292}
#     }

# <headingcell level=2>

# Start by looking at a small subset of keys from valid_segments[0]

# <markdowncell>

# Since it can take 10-50 seconds or so to retrieve all the keys in a valid segment, it's worth limiting to say first 10 to get a feel for what you can do with a key.  Run the following:

# <codecell>

from itertools import islice

import boto
from boto.s3.connection import S3Connection

conn = S3Connection()
bucket = conn.get_bucket('aws-publicdatasets')
for key in islice(bucket.list(prefix="common-crawl/parse-output/segment/1346823845675/", delimiter="/"),10):
    print key.name.encode('utf-8')

# <codecell>

# WARNING -- this might take a bit of time to run -- run it to see how long it takes you to get all the keys in this
# segment.  time depends on where you are running this code

%time all_files = list(islice(bucket.list(prefix="common-crawl/parse-output/segment/1346823845675/", delimiter="/"),None))
print len(all_files), all_files[0]

# <markdowncell>

# But it's useful now to have `all_files` to hold all the keys under the segment `1346823845675`  Note, for example, you can get the size of the file and the name -- and the type of file (boto.s3.key.Key)

# <codecell>

# http://boto.readthedocs.org/en/latest/ref/s3.html#module-boto.s3.key

file0 = all_files[0]
type(file0), file0.name, file0.size

# <codecell>

import boto
from boto.s3.connection import S3Connection

from itertools import islice
from pandas import DataFrame

conn= S3Connection()
bucket = conn.get_bucket('aws-publicdatasets')

# you might find this conversion function between DataFrame and a list of a regular dict useful
#https://gist.github.com/mikedewar/1486027#comment-804797
def df_to_dictlist(df):
    return [{k:df.values[i][v] for v,k in enumerate(df.columns)} for i in range(len(df))]

def cc_file_type(path):

    fname = path.split("/")[-1]
    
    if fname[-7:] == '.arc.gz':
        return 'arc.gz'
    elif fname[:9] == 'textData-':
        return 'textData'
    elif fname[:9] == 'metadata-':
        return 'metadata'
    elif fname == '_SUCCESS':
        return 'success'
    else:
        return 'other'
    
# a first pass, using DataFrame.  Might not be so efficient considering we are returning only totals
def segment_stats(seg_id, stop=None):
    all_files = islice(bucket.list(prefix="common-crawl/parse-output/segment/{0}/".format(seg_id), delimiter="/"),stop)
    df = DataFrame([{'size': f.size if hasattr(f, 'size') else 0, 'name':f.name, 'type':cc_file_type(f.name)} for f in all_files])
    return {'count': df_to_dictlist(df[['size','type']].groupby('type').count()[['size']].T)[0],
            'size': df_to_dictlist(df[['size', 'type']].groupby('type').sum().astype('int64').T)[0]}
    

# <codecell>

# another version of segment_stats that doesn't use DataFrame; probably easier to comprehend what's going on too -- and possibly
# faster

def segment_stats2(seg_id, stop=None):
    from collections import Counter
    file_count = Counter()
    byte_count = Counter()
    
    all_files = islice(bucket.list(prefix="common-crawl/parse-output/segment/{0}/".format(seg_id), delimiter="/"),stop)
    for f in all_files:
        file_type = cc_file_type(f.name)
        file_count.update({file_type: 1})
        byte_count.update({file_type: f.size if hasattr(f, 'size') else 0})
    
    return {'count': dict(file_count),
            'size': dict(byte_count)}

# <headingcell level=1>

# Running segment_status locally and on PiCloud

# <codecell>

# recall the first segment -- let's work on that segment
valid_segments[0]

# <codecell>

# look at how long it takes to run locally

%time segment_stats(valid_segments[0], None)

# <headingcell level=1>

# Rewrite to use multyvac instead of picloud

# <codecell>

import multyvac
jid = multyvac.submit(segment_stats, '1346823845675', _layer='numpy2')
jid

# <codecell>

job = multyvac.get(jid)
job.get_result()

# <codecell>

# pull up status -- refresh until done
job.status

# <codecell>

# this will block until job is done or errors out
job.wait()
#cloud.join(jid)

# <codecell>

# get your result
#cloud.result(jid)

job.get_result()

# <codecell>

# get useful info about job
# http://docs.multyvac.com/primer_python.html#more-attributes

[attr_ for attr_ in dir(job) if not attr_.startswith("_")]

# <codecell>

(job.created_at, job.finished_at, job.runtime, job.cputime_system, job.cputime_user)

# <codecell>

# get some specific info
# cloud.info(jid, info_requested=['created', 'finished', 'runtime', 'cputime'])

# <headingcell level=1>

# Writing code to submit a series of jobs

# <codecell>

import time, datetime
datetime.datetime.now().isoformat()

# <codecell>

import uuid
from itertools import islice

import multyvac

segments_to_calculate = list(islice(valid_segments,2))
job_name = uuid.uuid4().hex

segments_to_calculate
job_ids = [multyvac.submit(segment_stats, seg_id,
                           _name=job_name, _layer='numpy2',
                           _tags={'f':'segment_stats', 'args':seg_id}) for seg_id in \
           segments_to_calculate]

job_ids

# <codecell>

# let's get the results

multyvac.list(name=job_name)

# <headingcell level=1>

# What I got the first time

# <markdowncell>

# I had to retry 2 jobs
# 
# * https://www.picloud.com/accounts/jobs/#/?ujid=344 -> read timed out
# * 375 -> AttributeError: 'Prefix' object has no attribute 'size'

# <codecell>

# now tally everything noting the retries -- might be worth writing this generally
# THIS CODE REFERS SPECIFICALLY TO RAYMOND YEE'S JOBS -- REPLACE WITH YOUR OWN IDS

from pandas import DataFrame

import cloud
from itertools import izip, ifilter, chain, islice

from matplotlib import pyplot as plt

valid_segments
segment_jids = xrange(319, 496)
retries_seg_ids = ['1346876860789', '1350433106986']
retries_jids  = xrange(496, 498)

tally = list(ifilter(lambda x: x[2] == 'done', 
             izip(chain(valid_segments, retries_seg_ids), chain(segment_jids, retries_jids), 
          cloud.status(list(chain(segment_jids, retries_jids))))))

result = cloud.result([jid for (seg_id, jid, status) in tally])

# http://docs.picloud.com/moduledoc.html#module-cloud

jobs_info = cloud.info(list(islice(chain(segment_jids, retries_jids),None)),
                 info_requested=['created', 'finished', 'runtime', 'cputime', 'core']
                 )

started = [{'jid':k, 'time':v['finished'] - datetime.timedelta(seconds=v['runtime']), 'count': 1} for (k,v) in jobs_info.items()]
finished = [{'jid':k, 'time':v['finished'], 'count': -1} for (k,v) in jobs_info.items()]

df = DataFrame(started + finished)

exclude_n = 4

plot(df.sort_index(by='time')['time'][:-exclude_n], df.sort_index(by='time')['count'].cumsum()[:-exclude_n])

# <codecell>

from collections import Counter

file_counter = Counter()
byte_counter = Counter()

result = cloud.result([jid for (seg_id, jid, status) in tally])

for r in result:
    file_counter.update(r['count'])
    byte_counter.update(r['size'])
    
file_counter, byte_counter

# <codecell>

jobs_info

# <codecell>

from collections import Counter
jobs_counter= Counter()
[jobs_counter.update(dict([(k, v[k]) for k in ('cputime.system', 'cputime.user', 'runtime')])) for v in jobs_info.values()]
jobs_counter

#print (jobs_counter['cputime.user'] + jobs_counter['cputime.system']), (jobs_counter['cputime.user'] + jobs_counter['cputime.system'])/3600. * 0.05
print jobs_counter['runtime'], (jobs_counter['runtime'])/3600. * 0.05

# <codecell>

# maybe use pickle to serialize results
import pickle
s = pickle.loads(pickle.dumps(dict(zip([seg_id for (seg_id, jid, status) in tally], result))))

# <headingcell level=1>

# picloud job infos

# <codecell>

# http://docs.picloud.com/moduledoc.html#module-cloud

jobs_info = cloud.info(list(islice(chain(segment_jids, retries_jids),None)),
                 info_requested=['created', 'finished', 'runtime', 'cputime']
                 )

# <codecell>

from matplotlib import pyplot as plt

# <codecell>

started = [{'jid':k, 'time':v['finished'] - datetime.timedelta(seconds=v['runtime']), 'count': 1} for (k,v) in jobs_info.items()]
finished = [{'jid':k, 'time':v['finished'], 'count': -1} for (k,v) in jobs_info.items()]

df = DataFrame(started + finished)

exclude_n = 4

plot(df.sort_index(by='time')['time'][:-exclude_n], df.sort_index(by='time')['count'].cumsum()[:-exclude_n])

# <headingcell level=1>

# Try to do this better with automated retry and using cloud.iresult

# <markdowncell>

# run jobs locally using cloud.mp

# <codecell>

# http://docs.picloud.com/cloud_cloudmp.html 

USE_LOCAL = False

if USE_LOCAL:
    CLOUD = cloud.mp
else:
    CLOUD = cloud

# try setting n_tasks to something less than # of all segments to test out code

n_tasks = len(valid_segments)

jids = CLOUD.map(segment_stats2, valid_segments[:n_tasks],  [None]*n_tasks, _env='Working_with_Open_Data')

# <codecell>

jids

# <codecell>

CLOUD.status(jids)[:5]

# <codecell>

jobs_info = CLOUD.info(jids,
                 info_requested=['created', 'finished', 'runtime', 'cputime']
                 )

from collections import Counter
jobs_counter= Counter()
[jobs_counter.update(dict([(k, v[k]) for k in ('cputime.system', 'cputime.user', 'runtime')])) for v in jobs_info.values()]
jobs_counter

#print (jobs_counter['cputime.user'] + jobs_counter['cputime.system']), (jobs_counter['cputime.user'] + jobs_counter['cputime.system'])/3600. * 0.05
print "total runtime (s): ", jobs_counter['runtime'], "estimated cost: ", (jobs_counter['runtime'])/3600. * 0.05

# <codecell>

# plot # cores running vs time

started = [{'jid':k, 'time':v['finished'] - datetime.timedelta(seconds=v['runtime']), 'count': 1} for (k,v) in jobs_info.items()]
finished = [{'jid':k, 'time':v['finished'], 'count': -1} for (k,v) in jobs_info.items()]

df = DataFrame(started + finished)

plot(df.sort_index(by='time')['time'], df.sort_index(by='time')['count'].cumsum())

# <codecell>

byte_counter, file_counter

# <codecell>

# http://stackoverflow.com/a/1823101/7782

import locale
locale.setlocale(locale.LC_ALL, 'en_US')

locale.format("%d", byte_counter['arc.gz'],  grouping=True)

# <codecell>


