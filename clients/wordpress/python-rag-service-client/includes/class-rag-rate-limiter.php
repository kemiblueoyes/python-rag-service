<?php
/**
 * Site-wide fixed-window limits for the public Search and Ask routes.
 *
 * Each route has one row in the WordPress database. The stored minute only
 * moves forward, so a delayed worker can't recreate an exhausted minute after
 * cleanup. Admission is decided inside that upsert, not from the affected-row
 * count, so CLIENT_FOUND_ROWS can't turn a full window into a new admission.
 * The plugin doesn't change the shared connection's client flags.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Storage used by the rate limiter.
 */
interface RAG_Service_Rate_Limit_Database {

	/**
	 * Reserve one request in the window.
	 *
	 * True means the request was admitted. False means it was rejected.
	 * Null means storage failed.
	 *
	 * A rejected reservation includes a full window and a minute older than
	 * the minute already stored for the route.
	 *
	 * @param string $route         Route name, `search` or `answer`.
	 * @param int    $window_start  Unix time at the start of the minute.
	 * @param int    $limit         Maximum admitted requests in the window.
	 * @return bool|null
	 */
	public function reserve( string $route, int $window_start, int $limit ): ?bool;

	/**
	 * Drop a route's older row only when that route already has a newer one.
	 *
	 * The current row for a route is its watermark. Cleanup must not delete
	 * it, or a delayed worker could insert the exhausted minute again.
	 *
	 * @param int $window_start Unix time at the start of the caller's minute.
	 */
	public function delete_windows_before( int $window_start ): void;
}

/**
 * MySQL storage backed by the WordPress database.
 */
class RAG_Service_Wpdb_Rate_Limit_Database implements RAG_Service_Rate_Limit_Database {

	/**
	 * Reserve one request with a single conditional upsert.
	 *
	 * The session variable is connection-local. It is set before the upsert
	 * so a new row stays admitted, then overwritten by the update when the
	 * row already exists. The affected-row count is ignored.
	 *
	 * `request_count` is assigned before `window_start`. MySQL uses the
	 * updated value of an earlier assignment, and the count decision has to
	 * see the minute that was stored before this statement.
	 *
	 * @param string $route        Route name.
	 * @param int    $window_start Window start.
	 * @param int    $limit        Maximum admitted requests.
	 * @return bool|null
	 */
	public function reserve( string $route, int $window_start, int $limit ): ?bool {
		global $wpdb;

		$table = $this->table_name();
		if ( '' === $table || ! is_object( $wpdb ) || ! method_exists( $wpdb, 'prepare' ) || ! method_exists( $wpdb, 'get_var' ) ) {
			return null;
		}

		if ( false === $wpdb->query( 'SET @rag_service_rate_limit_admitted = 1' ) ) {
			return null;
		}

		$prepared = $wpdb->prepare(
			"INSERT INTO {$table} (route, window_start, request_count) VALUES (%s, %d, 1) ON DUPLICATE KEY UPDATE request_count = IF(window_start < VALUES(window_start), IF(@rag_service_rate_limit_admitted := 1, 1, 1), IF(window_start > VALUES(window_start), IF(@rag_service_rate_limit_admitted := 0, request_count, request_count), IF(@rag_service_rate_limit_admitted := request_count < %d, request_count + 1, request_count))), window_start = IF(window_start < VALUES(window_start), VALUES(window_start), window_start)",
			$route,
			$window_start,
			$limit
		);
		if ( false === $wpdb->query( $prepared ) ) {
			return null;
		}

		$admitted = $wpdb->get_var( 'SELECT @rag_service_rate_limit_admitted' );
		if ( '1' === (string) $admitted ) {
			return true;
		}
		if ( '0' === (string) $admitted ) {
			return false;
		}

		return null;
	}

	/**
	 * Delete expired windows.
	 *
	 * @param int $window_start Current window start.
	 */
	public function delete_windows_before( int $window_start ): void {
		global $wpdb;

		$table = $this->table_name();
		if ( '' === $table || ! is_object( $wpdb ) || ! method_exists( $wpdb, 'prepare' ) ) {
			return;
		}

		$wpdb->query(
			$wpdb->prepare(
				"DELETE old_rows FROM {$table} AS old_rows INNER JOIN {$table} AS current_rows ON old_rows.route = current_rows.route AND old_rows.window_start < current_rows.window_start WHERE old_rows.window_start < %d",
				$window_start
			)
		);
	}

	/**
	 * Table name, or an empty string when the prefix isn't safe to interpolate.
	 *
	 * @return string
	 */
	private function table_name(): string {
		global $wpdb;

		if ( ! is_object( $wpdb ) || ! isset( $wpdb->prefix ) ) {
			return '';
		}

		$table = $wpdb->prefix . 'rag_service_rate_limits';
		if ( ! is_string( $table ) || ! preg_match( '/^[A-Za-z0-9_]+$/', $table ) ) {
			return '';
		}

		return $table;
	}
}

/**
 * Fixed one-minute windows shared by every visitor on a route.
 */
class RAG_Service_Rate_Limiter {

	private const WINDOW_SECONDS = 60;

	/**
	 * Database that performs the atomic reservation.
	 *
	 * @var RAG_Service_Rate_Limit_Database
	 */
	private RAG_Service_Rate_Limit_Database $database;

	/**
	 * Create a limiter.
	 *
	 * @param RAG_Service_Rate_Limit_Database $database Shared storage.
	 */
	public function __construct( RAG_Service_Rate_Limit_Database $database ) {
		$this->database = $database;
	}

	/**
	 * Reserve one forwarded request.
	 *
	 * Returns null when storage fails. The caller doesn't forward in that case.
	 * `allowed` is false when the window is full. `retry_after` is the whole
	 * remaining window, in seconds.
	 *
	 * A new minute starts a new counter. Requests at the end of one minute and
	 * the start of the next can each use a full allowance.
	 *
	 * @param string $route Route name.
	 * @param int    $limit Positive request limit.
	 * @param int    $now   Current unix time.
	 * @return array{allowed: bool, retry_after: int}|null
	 */
	public function reserve( string $route, int $limit, int $now ): ?array {
		if ( $limit < 1 || $now < 0 ) {
			return null;
		}

		$window_start = $now - ( $now % self::WINDOW_SECONDS );
		$admitted     = $this->database->reserve( $route, $window_start, $limit );
		if ( null === $admitted ) {
			return null;
		}

		$this->database->delete_windows_before( $window_start );

		$retry_after = $window_start + self::WINDOW_SECONDS - $now;
		if ( $retry_after < 1 ) {
			$retry_after = 1;
		}

		return array(
			'allowed'     => $admitted,
			'retry_after' => $retry_after,
		);
	}
}

/**
 * Positive per-minute limit for a public route.
 *
 * An undefined constant uses the default. Any other value that isn't an
 * integer of 1 or greater is invalid, and the caller fails closed.
 *
 * @param string $route `search` or `answer`.
 * @return int|null
 */
function rag_service_configured_limit( string $route ): ?int {
	if ( 'search' === $route ) {
		$constant_name = 'RAG_SERVICE_SEARCH_REQUESTS_PER_MINUTE';
		$default       = 30;
	} elseif ( 'answer' === $route ) {
		$constant_name = 'RAG_SERVICE_ANSWER_REQUESTS_PER_MINUTE';
		$default       = 10;
	} else {
		return null;
	}

	if ( ! defined( $constant_name ) ) {
		return $default;
	}

	$value = constant( $constant_name );
	if ( is_int( $value ) && $value >= 1 ) {
		return $value;
	}

	return null;
}

/**
 * Unicode code points in a query.
 *
 * This counts code points, including combining marks. It doesn't count
 * UTF-8 bytes or grapheme clusters. Null means the length couldn't be measured.
 *
 * @param string $value Query text.
 * @return int|null
 */
function rag_service_unicode_length( string $value ): ?int {
	if ( function_exists( 'mb_strlen' ) ) {
		$length = mb_strlen( $value, 'UTF-8' );
		if ( is_int( $length ) ) {
			return $length;
		}
	}

	return rag_service_unicode_length_without_mbstring( $value );
}

/**
 * Code-point length when mbstring isn't available.
 *
 * @param string $value Query text.
 * @return int|null
 */
function rag_service_unicode_length_without_mbstring( string $value ): ?int {
	$length = preg_match_all( '/./u', $value, $matches );
	if ( false === $length ) {
		return null;
	}

	return $length;
}

/**
 * Option that records a created rate-limit table.
 *
 * @return string
 */
function rag_service_rate_limit_schema_option(): string {
	return 'rag_service_rate_limit_schema';
}

/**
 * Schema version created by this plugin.
 *
 * @return string
 */
function rag_service_rate_limit_schema_version(): string {
	return '2';
}

/**
 * CREATE TABLE statement for dbDelta.
 *
 * @param string $table_name       Prefixed table name.
 * @param string $charset_collate  WordPress charset clause.
 * @return string
 */
function rag_service_rate_limit_schema_sql( string $table_name, string $charset_collate ): string {
	return "CREATE TABLE {$table_name} (
  route varchar(32) NOT NULL,
  window_start bigint(20) unsigned NOT NULL,
  request_count bigint(20) unsigned NOT NULL,
  PRIMARY KEY  (route)
) ENGINE=InnoDB {$charset_collate};";
}

/**
 * Create the rate-limit table when it isn't already recorded.
 *
 * An already-active plugin doesn't run the activation hook again after the
 * files are copied. `plugins_loaded` calls this until the schema option is set.
 */
function rag_service_install_rate_limit_storage(): void {
	global $wpdb;

	if ( ! is_object( $wpdb ) || ! isset( $wpdb->prefix ) || ! method_exists( $wpdb, 'get_charset_collate' ) ) {
		return;
	}

	$table = $wpdb->prefix . 'rag_service_rate_limits';
	if ( ! is_string( $table ) || ! preg_match( '/^[A-Za-z0-9_]+$/', $table ) ) {
		return;
	}

	if ( ! function_exists( 'dbDelta' ) ) {
		$upgrade = ABSPATH . 'wp-admin/includes/upgrade.php';
		if ( ! is_readable( $upgrade ) ) {
			return;
		}
		require_once $upgrade;
	}

	$installed = (string) get_option( rag_service_rate_limit_schema_option(), '' );
	if ( rag_service_rate_limit_schema_version() !== $installed ) {
		$wpdb->query( "DROP TABLE IF EXISTS {$table}" );
	}

	dbDelta( rag_service_rate_limit_schema_sql( $table, $wpdb->get_charset_collate() ) );

	$found = $wpdb->get_var( $wpdb->prepare( 'SHOW TABLES LIKE %s', $wpdb->esc_like( $table ) ) );
	if ( $found === $table ) {
		update_option( rag_service_rate_limit_schema_option(), rag_service_rate_limit_schema_version() );
	}
}

/**
 * Create the table on the next request after an update.
 */
function rag_service_maybe_install_rate_limit_storage(): void {
	$installed = get_option( rag_service_rate_limit_schema_option(), '' );
	if ( rag_service_rate_limit_schema_version() === (string) $installed ) {
		return;
	}

	rag_service_install_rate_limit_storage();
}
