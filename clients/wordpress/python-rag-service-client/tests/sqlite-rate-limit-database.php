<?php
/**
 * SQLite storage for the plugin rate limiter.
 *
 * This is the test double's shared database. It follows the same minute
 * rules as the MySQL limiter: one row per route, the minute only moves
 * forward, and a full minute is rejected. It does not execute the production
 * MySQL statement. MySQL coverage lives in run-mysql-tests.php.
 */

if ( ! defined( 'ABSPATH' ) ) {
	define( 'ABSPATH', dirname( __DIR__ ) . '/' );
}

require_once dirname( __DIR__ ) . '/includes/class-rag-rate-limiter.php';

/**
 * Real SQLite database shared by concurrent PHP processes.
 */
class Rag_Sqlite_Rate_Limit_Database implements RAG_Service_Rate_Limit_Database {

	/**
	 * Open or create the database file.
	 *
	 * @param string $path SQLite file path.
	 */
	public function __construct( string $path ) {
		$this->pdo = new PDO(
			'sqlite:' . $path,
			null,
			null,
			array( PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION )
		);
		$this->pdo->exec( 'PRAGMA busy_timeout = 5000' );
		$this->pdo->exec( 'PRAGMA journal_mode = WAL' );
	}

	/**
	 * Create the limiter table.
	 */
	public function create_table(): void {
		$this->pdo->exec(
			'CREATE TABLE IF NOT EXISTS rag_service_rate_limits (
				route TEXT NOT NULL,
				window_start INTEGER NOT NULL,
				request_count INTEGER NOT NULL,
				admit_flag INTEGER NOT NULL,
				PRIMARY KEY (route)
			)'
		);
	}

	/**
	 * Reserve one request.
	 *
	 * `RETURNING` belongs to this statement, so another connection can't overwrite it.
	 *
	 * @param string $route        Route name.
	 * @param int    $window_start Window start.
	 * @param int    $limit        Maximum admitted requests.
	 * @return bool|null
	 */
	public function reserve( string $route, int $window_start, int $limit ): ?bool {
		try {
			$statement = $this->pdo->prepare(
				'INSERT INTO rag_service_rate_limits (route, window_start, request_count, admit_flag)
				 VALUES (:route, :window_start, 1, 1)
				 ON CONFLICT(route) DO UPDATE SET
				 admit_flag = CASE
				   WHEN rag_service_rate_limits.window_start < excluded.window_start THEN 1
				   WHEN rag_service_rate_limits.window_start > excluded.window_start THEN 0
				   WHEN rag_service_rate_limits.request_count < :under_limit THEN 1
				   ELSE 0
				 END,
				 request_count = CASE
				   WHEN rag_service_rate_limits.window_start < excluded.window_start THEN 1
				   WHEN rag_service_rate_limits.window_start > excluded.window_start THEN rag_service_rate_limits.request_count
				   WHEN rag_service_rate_limits.request_count < :under_limit_count THEN rag_service_rate_limits.request_count + 1
				   ELSE rag_service_rate_limits.request_count
				 END,
				 window_start = CASE
				   WHEN rag_service_rate_limits.window_start < excluded.window_start THEN excluded.window_start
				   ELSE rag_service_rate_limits.window_start
				 END
				 RETURNING admit_flag'
			);
			$statement->execute(
				array(
					':route'             => $route,
					':window_start'      => $window_start,
					':under_limit'       => $limit,
					':under_limit_count' => $limit,
				)
			);
			$flag = $statement->fetchColumn();
			if ( false === $flag ) {
				return null;
			}
			return 1 === (int) $flag;
		} catch ( PDOException $exception ) {
			return null;
		}
	}

	/**
	 * Delete expired windows.
	 *
	 * @param int $window_start Current window start.
	 */
	public function delete_windows_before( int $window_start ): void {
		unset( $window_start );
		// One row per route cannot be an older sibling of itself. The production
		// MySQL cleanup is a self-join and is covered by run-mysql-tests.php.
	}

	/**
	 * Rows currently stored.
	 *
	 * @return array<int, array<string, mixed>>
	 */
	public function rows(): array {
		return $this->pdo->query(
			'SELECT route, window_start, request_count
			 FROM rag_service_rate_limits
			 ORDER BY route, window_start'
		)->fetchAll( PDO::FETCH_ASSOC );
	}

	/**
	 * Close the database so the file can be removed.
	 */
	public function close(): void {
		$this->pdo = null;
	}

	/**
	 * @var PDO|null
	 */
	private ?PDO $pdo = null;
}
