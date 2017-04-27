#!/usr/bin/perl -w

$|=1;

use strict;

use FindBin;

use lib "$FindBin::Bin/..";

use Constants;
use Readonly;
Readonly my $CONSTANTS => get_constants_hash();
use Getopt::Long;
use feature qw( switch );
use vars qw( @flags );
use constant{
    FALSE => 0,
    TRUE  => 1,
};

####FUNCTIONS####
sub local_usage($)
{
    my ( $message ) = @_;

    print STDERR "$message\n";
    print STDERR "Usage: get_db_info.pl <OPTIONS>\n";
    print STDERR "By default this script returns all values in the order below.\n";
    print STDERR "Spcefying flags will return in the flag order.\n";
    print STDERR "    -h | --host : print the host name\n";
    print STDERR "    -p | --port : print the port name\n";
    print STDERR "    -n | --name : print the db name\n";
    print STDERR "    -u | --user : print the db username\n";
    print STDERR "         --help : print this usage text\n";
    print STDERR "\n";

    die 1;
}

sub arg_handler
{
    my ( $arg_name, $arg_value ) = @_;

    push( @flags, $arg_name );
}

sub parse_args
{
    # set defaults
    my $help = FALSE;

    # get options
    GetOptions (
        "host|h" => \&arg_handler,
        "port|p" => \&arg_handler,
        "name|n" => \&arg_handler,
        "user|u" => \&arg_handler,
        "help"   => \$help,
    ) or local_usage( "Failed to get options." );

    # check arguments
    if ( $help == TRUE )
    {
        local_usage( "" );
    }
}

####MAIN PROGRAM####
parse_args();

if( scalar @flags > 0 )
{
    foreach my $flag (@flags)
    {
        given($flag)
        {
            when(/(h|host)/)
            {
                print $CONSTANTS->{DBASE_HOSTNAME}, "\n";
            }

            when(/(p|port)/)
            {
                print $CONSTANTS->{DBASE_PORT}, "\n";
            }

            when(/(n|name)/)
            {
                print $CONSTANTS->{DBASE_SID}, "\n";
            }

            when(/(u|user)/)
            {
                print $CONSTANTS->{DBASE_USERNAME}, "\n";
            }

            default
            {
                print "\n";
            }
        }
    }
}
else
{
    print $CONSTANTS->{DBASE_HOSTNAME}, "\n";
    print $CONSTANTS->{DBASE_PORT}, "\n";
    print $CONSTANTS->{DBASE_SID}, "\n";
    print $CONSTANTS->{DBASE_USERNAME}, "\n";
}

exit 0;
