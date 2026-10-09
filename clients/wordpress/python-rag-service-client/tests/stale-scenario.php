<?php
/**
 * Deterministic stale-window sequence.
 *
 * The delayed worker is paused before it reserves. Another worker then moves
 * a route into the next minute, which runs cleanup. The delayed worker resumes
 * with the original minute.
 *
 * @param RAG_Service_Rate_Limiter $limiter          Limiter under test.
 * @param callable                 $spawn            Starts the paused worker. Returns array{0: resource, 1: array<int, resource>}.
 * @param callable                 $rows             Returns the stored rows.
 * @param string                   $advancing_route Route that moves into the next minute.
 * @param int                      $old_time        Timestamp inside the exhausted minute.
 * @param int                      $new_time        Timestamp inside the next minute.
 * @param int                      $limit           Positive limit for both routes.
 * @return string[] Failure messages.
 */
function rag_test_stale_window(
	RAG_Service_Rate_Limiter $limiter,
	callable $spawn,
	callable $rows,
	string $advancing_route,
	int $old_time,
	int $new_time,
	int $limit
): array {
	$errors = array();
	for ( $i = 0; $i < $limit; $i++ ) {
		$decision = $limiter->reserve( 'search', $limit, $old_time );
		if ( ! is_array( $decision ) || true !== $decision['allowed'] ) {
			$errors[] = "search {$i} was not admitted while exhausting the old minute";
			return $errors;
		}
	}

	$started = $spawn();
	if ( ! is_resource( $started[0] ) ) {
		$errors[] = 'stale worker failed to start';
		return $errors;
	}

	$ready = $started[2];
	$deadline = microtime( true ) + 10;
	while ( ! is_file( $ready ) ) {
		if ( microtime( true ) > $deadline ) {
			proc_terminate( $started[0] );
			$errors[] = 'stale worker did not pause before reservation';
			return $errors;
		}
		usleep( 20000 );
	}

	$advanced = $limiter->reserve( $advancing_route, $limit, $new_time );
	if ( ! is_array( $advanced ) || true !== $advanced['allowed'] ) {
		proc_terminate( $started[0] );
		$errors[] = "{$advancing_route} did not move into the next minute";
		return $errors;
	}

	file_put_contents( $started[3], 'go' );
	$stdout = trim( (string) stream_get_contents( $started[1][1] ) );
	$stderr = trim( (string) stream_get_contents( $started[1][2] ) );
	fclose( $started[1][1] );
	fclose( $started[1][2] );
	proc_close( $started[0] );
	if ( '' !== $stderr ) {
		$errors[] = $stderr;
	}
	if ( 'exhausted' !== $stdout ) {
		$errors[] = "delayed search worker returned [{$stdout}] after {$advancing_route} cleanup";
	}

	$stored = array();
	foreach ( $rows() as $row ) {
		$stored[ $row['route'] ] = $row;
	}
	$old_window = $old_time - ( $old_time % 60 );
	$new_window = $new_time - ( $new_time % 60 );
	if ( 'search' === $advancing_route ) {
		if ( ! isset( $stored['search'] ) || (string) $stored['search']['window_start'] !== (string) $new_window || 1 !== (int) $stored['search']['request_count'] ) {
			$errors[] = 'same-route cleanup left search at ' . json_encode( $stored['search'] ?? null );
		}
		foreach ( $rows() as $row ) {
			if ( 'search' === $row['route'] && (string) $row['window_start'] === (string) $old_window ) {
				$errors[] = 'delayed worker recreated the exhausted search minute';
			}
		}
	} else {
		if ( ! isset( $stored['search'] ) || (string) $stored['search']['window_start'] !== (string) $old_window || $limit !== (int) $stored['search']['request_count'] ) {
			$errors[] = 'other-route cleanup changed the exhausted search row to ' . json_encode( $stored['search'] ?? null );
		}
		if ( ! isset( $stored['answer'] ) || (string) $stored['answer']['window_start'] !== (string) $new_window || 1 !== (int) $stored['answer']['request_count'] ) {
			$errors[] = 'other-route advance did not store the new ask minute';
		}
	}

	return $errors;
}
