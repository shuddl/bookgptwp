<?php

/**
 * The admin-specific functionality of the plugin.
 */
class BookGPT_Admin {

    /**
     * Register the stylesheets for the admin area.
     */
    public function enqueue_styles($hook) {
        // Only load on plugin pages
        if (strpos($hook, 'bookgpt') === false) {
            return;
        }
        
        wp_enqueue_style('bookgpt-admin', BOOKGPT_PLUGIN_URL . 'admin/css/bookgpt-admin.css', array(), BOOKGPT_VERSION, 'all');
        
        // Chart.js for analytics
        wp_enqueue_style('chartjs', 'https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.css', array(), '3.9.1', 'all');
    }

    /**
     * Register the JavaScript for the admin area.
     */
    public function enqueue_scripts($hook) {
        // Only load on plugin pages
        if (strpos($hook, 'bookgpt') === false) {
            return;
        }
        
        // Chart.js for analytics
        wp_enqueue_script('chartjs', 'https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js', array(), '3.9.1', true);
        
        wp_enqueue_script('bookgpt-admin', BOOKGPT_PLUGIN_URL . 'admin/js/bookgpt-admin.js', array('jquery', 'chartjs'), BOOKGPT_VERSION, true);
        
        // Pass Ajax URL and nonce to JS
        wp_localize_script('bookgpt-admin', 'bookgpt_admin', array(
            'ajax_url' => admin_url('admin-ajax.php'),
            'nonce' => wp_create_nonce('bookgpt-admin-nonce'),
        ));
    }

    /**
     * Add admin menu items
     */
    public function add_admin_menu() {
        // Main Dashboard
        add_menu_page(
            __('BookGPT Dashboard', 'bookgpt-wp'),
            __('BookGPT', 'bookgpt-wp'),
            'manage_options',
            'bookgpt-dashboard',
            array($this, 'display_dashboard_page'),
            'dashicons-book-alt',
            30
        );
        
        // Settings Page
        add_submenu_page(
            'bookgpt-dashboard',
            __('Settings', 'bookgpt-wp'),
            __('Settings', 'bookgpt-wp'),
            'manage_options',
            'bookgpt-settings',
            array($this, 'display_settings_page')
        );
        
        // Analytics Page
        add_submenu_page(
            'bookgpt-dashboard',
            __('Analytics', 'bookgpt-wp'),
            __('Analytics', 'bookgpt-wp'),
            'manage_options',
            'bookgpt-analytics',
            array($this, 'display_analytics_page')
        );
        
        // Backend Logic Page
        add_submenu_page(
            'bookgpt-dashboard',
            __('Backend Logic', 'bookgpt-wp'),
            __('Backend Logic', 'bookgpt-wp'),
            'manage_options',
            'bookgpt-backend-logic',
            array($this, 'display_backend_logic_page')
        );
        
        // Conversions & Affiliate Links Page
        add_submenu_page(
            'bookgpt-dashboard',
            __('Affiliate Links', 'bookgpt-wp'),
            __('Affiliate Links', 'bookgpt-wp'),
            'manage_options',
            'bookgpt-affiliate-links',
            array($this, 'display_affiliate_links_page')
        );
    }

    /**
     * Register plugin settings
     */
    public function register_settings() {
        register_setting('bookgpt_options_group', 'bookgpt_options');
        
        // API Settings
        add_settings_section(
            'bookgpt_api_settings',
            __('API Settings', 'bookgpt-wp'),
            array($this, 'api_settings_callback'),
            'bookgpt-settings'
        );
        
        add_settings_field(
            'api_url',
            __('API URL', 'bookgpt-wp'),
            array($this, 'api_url_callback'),
            'bookgpt-settings',
            'bookgpt_api_settings'
        );
        
        add_settings_field(
            'openai_api_key',
            __('OpenAI API Key', 'bookgpt-wp'),
            array($this, 'openai_api_key_callback'),
            'bookgpt-settings',
            'bookgpt_api_settings'
        );
        
        add_settings_field(
            'google_books_api_key',
            __('Google Books API Key', 'bookgpt-wp'),
            array($this, 'google_books_api_key_callback'),
            'bookgpt-settings',
            'bookgpt_api_settings'
        );
        
        // Widget Appearance Settings
        add_settings_section(
            'bookgpt_appearance_settings',
            __('Widget Appearance', 'bookgpt-wp'),
            array($this, 'appearance_settings_callback'),
            'bookgpt-settings'
        );
        
        add_settings_field(
            'chat_widget_title',
            __('Widget Title', 'bookgpt-wp'),
            array($this, 'chat_widget_title_callback'),
            'bookgpt-settings',
            'bookgpt_appearance_settings'
        );
        
        add_settings_field(
            'chat_widget_position',
            __('Widget Position', 'bookgpt-wp'),
            array($this, 'chat_widget_position_callback'),
            'bookgpt-settings',
            'bookgpt_appearance_settings'
        );
        
        add_settings_field(
            'chat_widget_color',
            __('Widget Color', 'bookgpt-wp'),
            array($this, 'chat_widget_color_callback'),
            'bookgpt-settings',
            'bookgpt_appearance_settings'
        );
        
        // Affiliate Settings
        add_settings_section(
            'bookgpt_affiliate_settings',
            __('Affiliate Settings', 'bookgpt-wp'),
            array($this, 'affiliate_settings_callback'),
            'bookgpt-settings'
        );
        
        add_settings_field(
            'amazon_associate_tag',
            __('Amazon Associate Tag', 'bookgpt-wp'),
            array($this, 'amazon_associate_tag_callback'),
            'bookgpt-settings',
            'bookgpt_affiliate_settings'
        );
        
        // Advanced Settings
        add_settings_section(
            'bookgpt_advanced_settings',
            __('Advanced Settings', 'bookgpt-wp'),
            array($this, 'advanced_settings_callback'),
            'bookgpt-settings'
        );
        
        add_settings_field(
            'enable_analytics',
            __('Enable Analytics', 'bookgpt-wp'),
            array($this, 'enable_analytics_callback'),
            'bookgpt-settings',
            'bookgpt_advanced_settings'
        );
        
        add_settings_field(
            'prompt_template',
            __('Prompt Template', 'bookgpt-wp'),
            array($this, 'prompt_template_callback'),
            'bookgpt-settings',
            'bookgpt_advanced_settings'
        );
        
        add_settings_field(
            'max_recommendations',
            __('Max Recommendations', 'bookgpt-wp'),
            array($this, 'max_recommendations_callback'),
            'bookgpt-settings',
            'bookgpt_advanced_settings'
        );
        
        add_settings_field(
            'enable_chat_history',
            __('Enable Chat History', 'bookgpt-wp'),
            array($this, 'enable_chat_history_callback'),
            'bookgpt-settings',
            'bookgpt_advanced_settings'
        );

        // Deployment Settings
        add_settings_section(
            'bookgpt_deployment_settings',
            __('Deployment Settings', 'bookgpt-wp'),
            array($this, 'deployment_settings_callback'),
            'bookgpt-settings'
        );

        add_settings_field(
            'vercel_token',
            __('Vercel Token', 'bookgpt-wp'),
            array($this, 'vercel_token_callback'),
            'bookgpt-settings',
            'bookgpt_deployment_settings'
        );

        add_settings_field(
            'vercel_project_id',
            __('Vercel Project ID', 'bookgpt-wp'),
            array($this, 'vercel_project_id_callback'),
            'bookgpt-settings',
            'bookgpt_deployment_settings'
        );

        add_settings_field(
            'vercel_org_id',
            __('Vercel Org ID', 'bookgpt-wp'),
            array($this, 'vercel_org_id_callback'),
            'bookgpt-settings',
            'bookgpt_deployment_settings'
        );
    }
    
    /**
     * API Settings section callback
     */
    public function api_settings_callback() {
        echo '<p>' . __('Configure the API endpoints and keys needed for the chatbot to function.', 'bookgpt-wp') . '</p>';
    }
    
    /**
     * API URL field callback
     */
    public function api_url_callback() {
        $options = get_option('bookgpt_options');
        ?>
        <input type='text' name='bookgpt_options[api_url]' class='regular-text' value='<?php echo esc_attr($options['api_url'] ?? ''); ?>'>
        <p class="description"><?php _e('URL of your BookGPT backend API (e.g., https://your-bookgpt-api.vercel.app/api/chat)', 'bookgpt-wp'); ?></p>
        <?php
    }
    
    /**
     * OpenAI API Key field callback
     */
    public function openai_api_key_callback() {
        $options = get_option('bookgpt_options');
        ?>
        <input type='password' name='bookgpt_options[openai_api_key]' class='regular-text' value='<?php echo esc_attr($options['openai_api_key'] ?? ''); ?>'>
        <p class="description"><?php _e('Your OpenAI API key for generating recommendations.', 'bookgpt-wp'); ?></p>
        <?php
    }
    
    /**
     * Google Books API Key field callback
     */
    public function google_books_api_key_callback() {
        $options = get_option('bookgpt_options');
        ?>
        <input type='password' name='bookgpt_options[google_books_api_key]' class='regular-text' value='<?php echo esc_attr($options['google_books_api_key'] ?? ''); ?>'>
        <p class="description"><?php _e('Your Google Books API key for fetching book details.', 'bookgpt-wp'); ?></p>
        <?php
    }
    
    /**
     * Appearance Settings section callback
     */
    public function appearance_settings_callback() {
        echo '<p>' . __('Customize how the chat widget appears on your site.', 'bookgpt-wp') . '</p>';
    }
    
    /**
     * Chat Widget Title field callback
     */
    public function chat_widget_title_callback() {
        $options = get_option('bookgpt_options');
        ?>
        <input type='text' name='bookgpt_options[chat_widget_title]' class='regular-text' value='<?php echo esc_attr($options['chat_widget_title'] ?? 'Book Recommendations'); ?>'>
        <?php
    }
    
    /**
     * Chat Widget Position field callback
     */
    public function chat_widget_position_callback() {
        $options = get_option('bookgpt_options');
        $position = $options['chat_widget_position'] ?? 'bottom-right';
        ?>
        <select name='bookgpt_options[chat_widget_position]'>
            <option value='bottom-right' <?php selected($position, 'bottom-right'); ?>><?php _e('Bottom Right', 'bookgpt-wp'); ?></option>
            <option value='bottom-left' <?php selected($position, 'bottom-left'); ?>><?php _e('Bottom Left', 'bookgpt-wp'); ?></option>
            <option value='top-right' <?php selected($position, 'top-right'); ?>><?php _e('Top Right', 'bookgpt-wp'); ?></option>
            <option value='top-left' <?php selected($position, 'top-left'); ?>><?php _e('Top Left', 'bookgpt-wp'); ?></option>
        </select>
        <?php
    }
    
    /**
     * Chat Widget Color field callback
     */
    public function chat_widget_color_callback() {
        $options = get_option('bookgpt_options');
        ?>
        <input type='color' name='bookgpt_options[chat_widget_color]' value='<?php echo esc_attr($options['chat_widget_color'] ?? '#3b82f6'); ?>'>
        <?php
    }
    
    /**
     * Affiliate Settings section callback
     */
    public function affiliate_settings_callback() {
        echo '<p>' . __('Configure your affiliate settings for monetization.', 'bookgpt-wp') . '</p>';
    }
    
    /**
     * Amazon Associate Tag field callback
     */
    public function amazon_associate_tag_callback() {
        $options = get_option('bookgpt_options');
        ?>
        <input type='text' name='bookgpt_options[amazon_associate_tag]' class='regular-text' value='<?php echo esc_attr($options['amazon_associate_tag'] ?? ''); ?>'>
        <p class="description"><?php _e('Your Amazon Associate tracking ID (e.g., yourname-20)', 'bookgpt-wp'); ?></p>
        <?php
    }
    
    /**
     * Advanced Settings section callback
     */
    public function advanced_settings_callback() {
        echo '<p>' . __('Advanced configuration options.', 'bookgpt-wp') . '</p>';
    }
    
    /**
     * Enable Analytics field callback
     */
    public function enable_analytics_callback() {
        $options = get_option('bookgpt_options');
        $enabled = $options['enable_analytics'] ?? 'yes';
        ?>
        <label>
            <input type='checkbox' name='bookgpt_options[enable_analytics]' value='yes' <?php checked($enabled, 'yes'); ?>>
            <?php _e('Track user interactions and API usage', 'bookgpt-wp'); ?>
        </label>
        <?php
    }
    
    /**
     * Prompt Template field callback
     */
    public function prompt_template_callback() {
        $options = get_option('bookgpt_options');
        $prompt = $options['prompt_template'] ?? 'You are a helpful book recommendation assistant. Analyze the user\'s preferences and suggest relevant books.';
        ?>
        <textarea name='bookgpt_options[prompt_template]' class='large-text' rows='4'><?php echo esc_textarea($prompt); ?></textarea>
        <p class="description"><?php _e('System prompt template used for generating recommendations.', 'bookgpt-wp'); ?></p>
        <?php
    }
    
    /**
     * Max Recommendations field callback
     */
    public function max_recommendations_callback() {
        $options = get_option('bookgpt_options');
        $max = $options['max_recommendations'] ?? 3;
        ?>
        <input type='number' name='bookgpt_options[max_recommendations]' min='1' max='5' value='<?php echo esc_attr($max); ?>'>
        <p class="description"><?php _e('Maximum number of book recommendations to show (1-5)', 'bookgpt-wp'); ?></p>
        <?php
    }
    
    /**
     * Enable Chat History field callback
     */
    public function enable_chat_history_callback() {
        $options = get_option('bookgpt_options');
        $enabled = $options['enable_chat_history'] ?? 'yes';
        ?>
        <label>
            <input type='checkbox' name='bookgpt_options[enable_chat_history]' value='yes' <?php checked($enabled, 'yes'); ?>>
            <?php _e('Remember conversation context within a session', 'bookgpt-wp'); ?>
        </label>
        <?php
    }

    /**
     * Deployment Settings section callback
     */
    public function deployment_settings_callback() {
        echo '<p>' . __('Configure the deployment settings for Vercel.', 'bookgpt-wp') . '</p>';
    }

    /**
     * Vercel Token field callback
     */
    public function vercel_token_callback() {
        $options = get_option('bookgpt_options');
        ?>
        <input type='password' name='bookgpt_options[vercel_token]' class='regular-text' value='<?php echo esc_attr($options['vercel_token'] ?? ''); ?>'>
        <p class="description"><?php _e('Your Vercel token for deployment.', 'bookgpt-wp'); ?></p>
        <?php
    }

    /**
     * Vercel Project ID field callback
     */
    public function vercel_project_id_callback() {
        $options = get_option('bookgpt_options');
        ?>
        <input type='text' name='bookgpt_options[vercel_project_id]' class='regular-text' value='<?php echo esc_attr($options['vercel_project_id'] ?? ''); ?>'>
        <p class="description"><?php _e('Your Vercel project ID.', 'bookgpt-wp'); ?></p>
        <?php
    }

    /**
     * Vercel Org ID field callback
     */
    public function vercel_org_id_callback() {
        $options = get_option('bookgpt_options');
        ?>
        <input type='text' name='bookgpt_options[vercel_org_id]' class='regular-text' value='<?php echo esc_attr($options['vercel_org_id'] ?? ''); ?>'>
        <p class="description"><?php _e('Your Vercel organization ID.', 'bookgpt-wp'); ?></p>
        <?php
    }

    /**
     * Display the main dashboard page
     */
    public function display_dashboard_page() {
        // Get analytics data
        $analytics = new BookGPT_Analytics();
        $total_conversations = $analytics->get_total_conversations();
        $total_recommendations = $analytics->get_total_recommendations();
        $total_clicks = $analytics->get_total_book_clicks();
        $click_through_rate = $analytics->get_clickthrough_rate();
        
        // Get API usage data
        $monthly_api_cost = $analytics->get_monthly_api_cost();
        $total_tokens = $analytics->get_total_tokens();
        
        include_once BOOKGPT_PLUGIN_DIR . 'admin/partials/dashboard-display.php';
    }
    
    /**
     * Display the settings page
     */
    public function display_settings_page() {
        include_once BOOKGPT_PLUGIN_DIR . 'admin/partials/settings-display.php';
    }
    
    /**
     * Display the analytics page
     */
    public function display_analytics_page() {
        $analytics = new BookGPT_Analytics();
        
        // Get chart data
        $conversation_data = $analytics->get_conversation_chart_data();
        $book_click_data = $analytics->get_book_click_chart_data();
        $api_usage_data = $analytics->get_api_usage_chart_data();
        $popular_books = $analytics->get_popular_books(10);
        
        include_once BOOKGPT_PLUGIN_DIR . 'admin/partials/analytics-display.php';
    }
    
    /**
     * Display the backend logic page
     */
    public function display_backend_logic_page() {
        include_once BOOKGPT_PLUGIN_DIR . 'admin/partials/backend-logic-display.php';
    }
    
    /**
     * Display the affiliate links page
     */
    public function display_affiliate_links_page() {
        $analytics = new BookGPT_Analytics();
        
        // Get affiliate link data
        $affiliate_stats = $analytics->get_affiliate_link_stats();
        $top_performing_books = $analytics->get_top_performing_books(10);
        
        include_once BOOKGPT_PLUGIN_DIR . 'admin/partials/affiliate-links-display.php';
    }
    
    /**
     * Ajax handler for fetching analytics data
     */
    public function ajax_get_analytics() {
        // Verify nonce
        if (!check_ajax_referer('bookgpt-admin-nonce', 'nonce', false)) {
            wp_send_json_error('Invalid security token');
        }
        
        $period = isset($_POST['period']) ? sanitize_text_field($_POST['period']) : '7days';
        $type = isset($_POST['type']) ? sanitize_text_field($_POST['type']) : 'conversations';
        
        $analytics = new BookGPT_Analytics();
        
        switch ($type) {
            case 'conversations':
                $data = $analytics->get_conversation_chart_data($period);
                break;
            case 'clicks':
                $data = $analytics->get_book_click_chart_data($period);
                break;
            case 'api_usage':
                $data = $analytics->get_api_usage_chart_data($period);
                break;
            default:
                $data = array();
        }
        
        wp_send_json_success($data);
    }
    
    /**
     * Ajax handler for updating backend logic
     */
    public function ajax_update_backend_logic() {
        // Verify nonce
        if (!check_ajax_referer('bookgpt-admin-nonce', 'nonce', false)) {
            wp_send_json_error('Invalid security token');
        }
        
        $prompt_template = isset($_POST['prompt_template']) ? sanitize_textarea_field($_POST['prompt_template']) : '';
        $max_recommendations = isset($_POST['max_recommendations']) ? intval($_POST['max_recommendations']) : 3;
        
        // Update options
        $options = get_option('bookgpt_options', array());
        $options['prompt_template'] = $prompt_template;
        $options['max_recommendations'] = $max_recommendations;
        
        update_option('bookgpt_options', $options);
        
        // Send updated logic to API if needed
        $api = new BookGPT_API();
        $result = $api->update_backend_logic($prompt_template, $max_recommendations);
        
        if (is_wp_error($result)) {
            wp_send_json_error($result->get_error_message());
        } else {
            wp_send_json_success('Backend logic updated successfully');
        }
    }
    
    /**
     * Ajax handler for testing API connection
     */
    public function ajax_test_api_connection() {
        // Verify nonce
        if (!check_ajax_referer('bookgpt-admin-nonce', 'nonce', false)) {
            wp_send_json_error('Invalid security token');
        }
        
        $api_url = isset($_POST['api_url']) ? esc_url_raw($_POST['api_url']) : '';
        
        if (empty($api_url)) {
            wp_send_json_error('API URL is required');
        }
        
        $api = new BookGPT_API();
        $result = $api->test_connection($api_url);
        
        if (is_wp_error($result)) {
            wp_send_json_error($result->get_error_message());
        } else {
            wp_send_json_success('API connection successful');
        }
    }
}
