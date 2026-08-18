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
$translated = $locales->getTranslator()->trans(
    'core.forum.header.search_placeholder',
    [],
    'messages',
    'ko'
);

if ($translated === 'core.forum.header.search_placeholder') {
    fwrite(STDERR, "Korean translation catalogue did not warm correctly\n");
    exit(1);
}

fwrite(STDOUT, "Korean catalogue warmed: {$translated}\n");
