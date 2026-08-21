#!/usr/bin/env perl
use strict;
use warnings;
use IO::Socket::INET;
use Cwd qw(abs_path);
use File::Basename qw(dirname);

my $port = $ARGV[0] || 8000;
my $dir = abs_path(dirname(__FILE__));

my %mime_types = (
    'html' => 'text/html; charset=UTF-8',
    'htm'  => 'text/html; charset=UTF-8',
    'css'  => 'text/css; charset=UTF-8',
    'js'   => 'application/javascript; charset=UTF-8',
    'csv'  => 'text/csv; charset=UTF-8',
    'json' => 'application/json; charset=UTF-8',
    'png'  => 'image/png',
    'jpg'  => 'image/jpeg',
    'svg'  => 'image/svg+xml',
    'txt'  => 'text/plain; charset=UTF-8'
);

my $server = IO::Socket::INET->new(
    LocalPort => $port,
    Type      => SOCK_STREAM,
    Reuse     => 1,
    Listen    => 10
) or die "Cannot create server on port $port: $!\n";

print "Server running at http://localhost:$port/ (serving $dir)\n";

while (my $client = $server->accept()) {
    my $request_line = <$client>;
    next unless defined $request_line;

    # Read and discard remaining request headers
    while (my $line = <$client>) {
        last if $line =~ /^\r?\n$/;
    }

    if ($request_line =~ m{^GET\s+([^\s\?]+)}) {
        my $path = $1;
        $path = '/index.html' if $path eq '/';
        $path =~ s{^/}{}; # remove leading slash
        $path =~ s{\.\.}{}g; # prevent directory traversal

        my $filepath = "$dir/$path";

        if (-f $filepath && open(my $fh, '<:raw', $filepath)) {
            my ($ext) = $path =~ m{\.([^.]+)$};
            $ext = lc($ext || '');
            my $content_type = $mime_types{$ext} || 'application/octet-stream';
            my $size = -s $filepath;

            print $client "HTTP/1.1 200 OK\r\n";
            print $client "Content-Type: $content_type\r\n";
            print $client "Content-Length: $size\r\n";
            print $client "Access-Control-Allow-Origin: *\r\n";
            print $client "Connection: close\r\n\r\n";

            my $buffer;
            while (read($fh, $buffer, 4096)) {
                print $client $buffer;
            }
            close($fh);
        } else {
            my $body = "404 Not Found: $path";
            my $size = length($body);
            print $client "HTTP/1.1 404 Not Found\r\n";
            print $client "Content-Type: text/plain\r\n";
            print $client "Content-Length: $size\r\n";
            print $client "Connection: close\r\n\r\n";
            print $client $body;
        }
    }
    close($client);
}
