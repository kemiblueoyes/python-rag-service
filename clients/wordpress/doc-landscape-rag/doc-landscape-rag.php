<?php
/**
 * Plugin Name: Doc Landscape RAG
 * Description: WordPress reference client for the Python RAG Service.
 * Version: 0.1.0
 * Author: Kemi Oyesiku
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

require_once plugin_dir_path( __FILE__ ) . 'includes/class-rag-api-client.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-rag-rest-controller.php';

function dl_rag_register_rest_routes() {
	$controller = new DL_RAG_REST_Controller();
	$controller->register_routes();
}

add_action( 'rest_api_init', 'dl_rag_register_rest_routes' );

/**
 * Render the RAG search and answer interface.
 */
function dl_rag_render_client() {
    wp_enqueue_style(
        'font-awesome-5',
        plugins_url( 'otter-blocks/assets/fontawesome/css/all.min.css' ),
        array()
    );
    wp_enqueue_style(
        'dl-rag-search',
        plugin_dir_url( __FILE__ ) . 'assets/rag-search.css',
        array( 'font-awesome-5' ),
        filemtime( plugin_dir_path( __FILE__ ) . 'assets/rag-search.css' )
    );
    wp_enqueue_script(
        'dl-rag-search',
        plugin_dir_url( __FILE__ ) . 'assets/rag-search.js',
        array(),
        filemtime( plugin_dir_path( __FILE__ ) . 'assets/rag-search.js' ),
        true
    );

	wp_localize_script(
		'dl-rag-search',
		'dlRagConfig',
		array(
			'searchUrl' => rest_url( 'doc-landscape-rag/v1/search' ),
			'answerUrl' => rest_url( 'doc-landscape-rag/v1/answer' ),
		)
	);

	ob_start();
	?>
	<div class="dl-rag-client">
		<form class="dl-rag-search-form">
			<label for="dl-rag-query">
				Search or ask The Doc Landscape
			</label>
            <p class="dl-rag-help">
                Search finds relevant passages. Ask generates an answer from the retrieved pages and articles.
            </p>
			<input
				id="dl-rag-query"
				class="dl-rag-query"
				type="search"
				name="query"
				required
			>

			<div class="dl-rag-actions">
				<button
					type="submit"
					data-mode="search"
				>
                <i class="fas fa-search"></i> Search
				</button>

				<button
					type="submit"
					data-mode="answer"
				>
                <i class="far fa-question-circle"></i> Ask
				</button>
			</div>
		</form>

		<div
			class="dl-rag-status"
			aria-live="polite"
		></div>

		<div class="dl-rag-results"></div>
	</div>
	<?php

	return ob_get_clean();
}
add_shortcode( 'doc_landscape_rag', 'dl_rag_render_client' );