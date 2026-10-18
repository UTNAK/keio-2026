package IdeaWall {
    part def Idea;
    part def Capture;
    part def Storage;
    part def Display;
    part def Analytics;

    part ideaWall {
        part capture : Capture;
        part storage : Storage;
        part display : Display;
        part analytics : Analytics;
    }
}

package IdeaWallViews {
    private import Views::*;

    view completeConcept {
        expose IdeaWall;
        expose IdeaWall::**;
    }
}
