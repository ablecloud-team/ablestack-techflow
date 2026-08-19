<?php

declare(strict_types=1);

use Flarum\Locale\LocaleManager;

$appRoot = $argv[1] ?? '';
$allowedRoot = getenv('TECHFLOW_ALLOWED_FLARUM_ROOT') ?: '/srv/techflow-flarum-staging/app';
if ($appRoot !== $allowedRoot) {
    fwrite(STDERR, "Unexpected Flarum application path\n");
    exit(2);
}

chdir($appRoot);
$site = require $appRoot.'/site.php';
$app = $site->bootApp();
$container = $app->getContainer();
$locales = $container->make(LocaleManager::class);
$translator = $locales->getTranslator();
$expected = ['core.forum.header.search_placeholder' => '검색'];
if (getenv('TECHFLOW_THEME_EXPECTED') === 'true') {
    $expected += [
        'core.forum.user.security_link' => '보안',
        'flarum-likes.forum.user.likes_link' => '좋아요',
        'fof-upload.forum.buttons.media' => '내 미디어',
    ];
}

foreach ($expected as $key => $value) {
    $translated = $translator->trans($key, [], 'messages', 'ko');
    if ($translated !== $value) {
        fwrite(STDERR, "Korean translation mismatch for {$key}: {$translated}\n");
        exit(1);
    }
}

fwrite(STDOUT, "Korean catalogue warmed: ".implode(', ', $expected)."\n");
