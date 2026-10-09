<?php
/**
 * SQLite storage for the plugin rate limiter.
 *
 * This is the test double's shared database. WordPress uses
 * RAG_Service_Wpdb_Rate_Limit_Database and MySQL. Both reserve with one
 * conditional upsert: insert 1, or increment only while the row is under the limit.
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
				PRIMARY KEY (route, window_start)
			)'
		);
	}

	/**
	 * Reserve one request.
	 *
	 * `changes()` is connection-local, so a concurrent writer doesn't overwrite it.
	 *
	 * @param string $route        Route name.
	 * @param int    $window_start Window start.
	 * @param int    $limit        Maximum admitted requests.
	 * @return int|null
	 */
	public function reserve( string $route, int $window_start, int $limit ): ?int {
		try {
			$statement = $this->pdo->prepare(
				'INSERT INTO rag_service_rate_limits (route, window_start, request_count)
				 VALUES (:route, :window_start, 1)
				 ON CONFLICT(route, window_start) DO UPDATE
				 SET request_count = request_count + 1
				 WHERE request_count < :limit'
			);
			$statement->execute(
				array(
					':route'        => $route,
					':window_start' => $window_start,
					':limit'        => $limit,
				)
			);
			return (int) $this->pdo->query( 'SELECT changes()' )->fetchColumn();
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
		try {
			$statement = $this->pdo->prepare(
				'DELETE FROM rag_service_rate_limits WHERE window_start < :window_start'
			);
			$statement->execute( array( ':window_start' => $window_start ) );
		} catch ( PDOException $exception ) {
			return;
		}
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
