<?php

use Flarum\Extend;

return [
    (new Extend\Frontend('forum'))
        ->css(__DIR__.'/resources/less/forum.less'),
    new Extend\Locales(__DIR__.'/locale'),
];
