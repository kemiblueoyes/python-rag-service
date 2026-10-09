<?php
/**
 * WordPress database adapter over a dedicated MySQL connection.
 *
 * The adapter does not change flags on any other connection. Tests that need
 * CLIENT_FOUND_ROWS open their own mysqli connection.
 */

if ( ! defined( 'ABSPATH' ) ) {
	define( 'ABSPATH', dirname( __DIR__ ) . '/' );
}

require_once dirname( __DIR__ ) . '/includes/class-rag-rate-limiter.php';

/**
 * Minimal wpdb stand-in for the production rate-limit class.
 */
class Rag_Mysqli_Wpdb {

	public string $prefix;
	public int $last_upsert_affected = -1;

	/**
	 * @param mysqli $connection Dedicated test connection.
	 * @param string $prefix     Table prefix.
	 */
	public function __construct( mysqli $connection, string $prefix ) {
		$this->connection = $connection;
		$this->prefix     = $prefix;
	}

	/**
	 * @param string $query SQL with placeholders.
	 * @param mixed  ...$args Placeholder values.
	 */
	public function prepare( string $query, mixed ...$args ): string {
		$offset = 0;
		$built  = preg_replace_callback(
			'/%[sdf]/',
			function ( array $match ) use ( $args, &$offset ): string {
				$value = $args[ $offset ];
				$offset++;
				if ( '%d' === $match[0] ) {
					return (string) (int) $value;
				}
				if ( '%f' === $match[0] ) {
					return (string) (float) $value;
				}
				return "'" . $this->connection->real_escape_string( (string) $value ) . "'";
			},
			$query
		);
		return is_string( $built ) ? $built : $query;
	}

	/**
	 * @param string $sql SQL.
	 * @return int|bool|mysqli_result
	 */
	public function query( string $sql ) {
		$result = $this->connection->query( $sql );
		if ( false === $result ) {
			return false;
		}
		if ( true === $result ) {
			if ( str_contains( $sql, 'ON DUPLICATE KEY UPDATE' ) ) {
				$this->last_upsert_affected = $this->connection->affected_rows;
			}
			return $this->connection->affected_rows;
		}
		return $result;
	}

	/**
	 * @param string $sql SQL.
	 */
	public function get_var( string $sql ): ?string {
		$result = $this->query( $sql );
		if ( ! $result instanceof mysqli_result ) {
			return null;
		}
		$row = $result->fetch_row();
		$result->free();
		if ( ! is_array( $row ) || ! array_key_exists( 0, $row ) || null === $row[0] ) {
			return null;
		}
		return (string) $row[0];
	}

	public function get_charset_collate(): string {
		return '';
	}

	public function esc_like( string $text ): string {
		return addcslashes( $text, '_%\\' );
	}

	/**
	 * @return array<int, array<string, string>>
	 */
	public function rate_rows(): array {
		$table  = $this->prefix . 'rag_service_rate_limits';
		$result = $this->connection->query(
			"SELECT route, window_start, request_count FROM {$table} ORDER BY route, window_start"
		);
		if ( ! $result instanceof mysqli_result ) {
			return array();
		}
		$rows = $result->fetch_all( MYSQLI_ASSOC );
		$result->free();
		return is_array( $rows ) ? $rows : array();
	}

	private mysqli $connection;
}

/**
 * Open the test database.
 *
 * @param int $flags mysqli client flags for this connection only.
 */
function rag_mysql_connect( int $flags ): mysqli {
	$host = getenv( 'RAG_TEST_MYSQL_HOST' );
	$user = getenv( 'RAG_TEST_MYSQL_USER' );
	$name = getenv( 'RAG_TEST_MYSQL_DATABASE' );
	if ( ! is_string( $host ) || '' === $host || ! is_string( $user ) || '' === $user || ! is_string( $name ) || '' === $name ) {
		fwrite( STDERR, "Set RAG_TEST_MYSQL_HOST, RAG_TEST_MYSQL_USER, and RAG_TEST_MYSQL_DATABASE.\n" );
		exit( 1 );
	}
	$password = getenv( 'RAG_TEST_MYSQL_PASSWORD' );
	$port     = getenv( 'RAG_TEST_MYSQL_PORT' );
	mysqli_report( MYSQLI_REPORT_OFF );
	$mysqli   = mysqli_init();
	$ok       = mysqli_real_connect(
		$mysqli,
		$host,
		$user,
		is_string( $password ) ? $password : '',
		$name,
		is_string( $port ) && '' !== $port ? (int) $port : 3306,
		null,
		$flags
	);
	if ( ! $ok ) {
		fwrite( STDERR, $mysqli->connect_error . "\n" );
		exit( 1 );
	}
	$mysqli->set_charset( 'utf8mb4' );
	return $mysqli;
}

/**
 * Point $wpdb at a new connection. Does not create or drop the table.
 *
 * @param int $flags mysqli client flags for this connection only.
 */
function rag_mysql_use( int $flags = 0 ): Rag_Mysqli_Wpdb {
	global $wpdb;

	$prefix = getenv( 'RAG_TEST_MYSQL_PREFIX' );
	if ( ! is_string( $prefix ) || 1 !== preg_match( '/^[A-Za-z0-9_]+$/', $prefix ) ) {
		fwrite( STDERR, "Set RAG_TEST_MYSQL_PREFIX to a safe table prefix.\n" );
		exit( 1 );
	}
	$wpdb = new Rag_Mysqli_Wpdb( rag_mysql_connect( $flags ), $prefix );
	return $wpdb;
}

/**
 * Replace the production table and return the production database class.
 *
 * @param int $flags mysqli client flags for the setup connection.
 */
function rag_mysql_production_database( int $flags = 0 ): RAG_Service_Wpdb_Rate_Limit_Database {
	$wpdb  = rag_mysql_use( $flags );
	$table = $wpdb->prefix . 'rag_service_rate_limits';
	$wpdb->query( "DROP TABLE IF EXISTS {$table}" );
	$created = $wpdb->query( rag_service_rate_limit_schema_sql( $table, '' ) );
	if ( false === $created ) {
		fwrite( STDERR, "Could not create {$table}.\n" );
		exit( 1 );
	}
	return new RAG_Service_Wpdb_Rate_Limit_Database();
}
