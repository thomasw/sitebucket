.. _todolist:

To Do List
**********

Duplicate Data / Loss of Data when Consolidating Streaming Connections
======================================================================

By default, the ListenerThreadMonitor will consolidate streaming connections
whenever there are enough non-maxed out connections to do so. Ideally, this process would work as follows:

1. Figure out how to minimize connections
2. Open up new, minimized connections but ignore their output.
3. Once their output matches the old thread's output, shut down the old threads and stop ignoring the new thread's output.

This is how it works right now:

1. Figure out how to minimize connections.
2. Start running the new threads and wait 30 seconds for them to initialize.
3. Shut down the old threads.

30 seconds may be too short or too long.

High Processor Usage on Initialization for high numbers of Listener Threads
===========================================================================

httplib's response object doesn't have a method for returning all data that's been downloaded 'so far'. You can either wait for the download to complete (which never happens because it's a stream), or consume the data X characters at a time.

The response object blocks if it hasn't yet received X characters. Because of this, Sitebucket has to consume the data returned by the stream 1 character at a time.

This causes really high CPU spikes when the stream is consuming large amounts of data. Unfortunately, this occurs regularly upon connection initialization because twitter sends a list of each user's followings.